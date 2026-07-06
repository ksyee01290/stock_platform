"""Endpoint tests for app.stocks.router.

Protected endpoints use the `auth_client` fixture (get_current_user overridden).
Public endpoints use the plain `client` fixture.
"""
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.stocks import models


def _add_stock(db, ticker="AAPL", name="Apple", price=150.0, high=200.0, low=100.0):
    stock = models.Stock(
        ticker=ticker,
        name=name,
        current_price=price,
        market_cap=1_000_000,
        high_52week=high,
        low_52week=low,
    )
    db.add(stock)
    db.commit()
    return stock


# --------------------------------------------------------------------------- #
# /search/recent  &  /search/trending
# --------------------------------------------------------------------------- #
def test_recent_searches_deduplicated_and_capped(client, db_session):
    base = datetime(2024, 1, 1, 12, 0, 0)
    # Insert 7 distinct tickers plus a duplicate, out of chronological order.
    tickers = ["A", "B", "C", "D", "E", "F", "A"]
    for i, t in enumerate(tickers):
        db_session.add(
            models.SearchHistory(ticker=t, searched_at=base + timedelta(minutes=i))
        )
    db_session.commit()

    resp = client.get("/api/stocks/search/recent")
    assert resp.status_code == 200
    data = resp.json()
    # capped at 5, most-recent-first, no duplicates
    returned = [d["ticker"] for d in data]
    assert len(returned) == 5
    assert len(set(returned)) == 5
    assert returned[0] == "A"  # most recent (the duplicate at minute 6)


def test_trending_searches_counts_and_orders(client, db_session):
    for _ in range(3):
        db_session.add(models.SearchHistory(ticker="HOT"))
    db_session.add(models.SearchHistory(ticker="COLD"))
    db_session.commit()

    resp = client.get("/api/stocks/search/trending")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0] == {"ticker": "HOT", "search_count": 3}
    counts = {d["ticker"]: d["search_count"] for d in data}
    assert counts["COLD"] == 1


def test_dashboard_init_combines_recent_and_trending(client, db_session):
    db_session.add(models.SearchHistory(ticker="AAPL"))
    db_session.commit()
    resp = client.get("/api/stocks/search/dashboard-init")
    assert resp.status_code == 200
    body = resp.json()
    assert "recent" in body and "trending" in body


# --------------------------------------------------------------------------- #
# /search/suggest
# --------------------------------------------------------------------------- #
def test_suggest_empty_query_returns_empty(client):
    assert client.get("/api/stocks/search/suggest?q=").json() == []
    assert client.get("/api/stocks/search/suggest?q=%20%20").json() == []


def test_suggest_matches_ticker_and_name(client, db_session):
    _add_stock(db_session, ticker="AAPL", name="Apple Inc")
    _add_stock(db_session, ticker="MSFT", name="Microsoft")

    by_ticker = client.get("/api/stocks/search/suggest?q=aap").json()
    assert any(item["ticker"] == "AAPL" for item in by_ticker)

    by_name = client.get("/api/stocks/search/suggest?q=micro").json()
    assert any(item["ticker"] == "MSFT" for item in by_name)


# --------------------------------------------------------------------------- #
# /watchlist toggle + list
# --------------------------------------------------------------------------- #
def test_watchlist_toggle_add_then_remove(auth_client, db_session):
    _add_stock(db_session, ticker="AAPL")

    added = auth_client.post("/api/stocks/watchlist/aapl")
    assert added.status_code == 200
    assert added.json()["is_favorite"] is True

    removed = auth_client.post("/api/stocks/watchlist/AAPL")
    assert removed.status_code == 200
    assert removed.json()["is_favorite"] is False


def test_watchlist_toggle_unknown_stock_404(auth_client):
    resp = auth_client.post("/api/stocks/watchlist/NOPE")
    assert resp.status_code == 404


def test_get_watchlist_returns_joined_data(auth_client, db_session):
    _add_stock(db_session, ticker="AAPL", name="Apple", price=150.0)
    auth_client.post("/api/stocks/watchlist/AAPL")

    resp = auth_client.get("/api/stocks/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["ticker"] == "AAPL"
    assert data[0]["current_price"] == 150.0


def test_watchlist_requires_auth(client, db_session):
    _add_stock(db_session, ticker="AAPL")
    # No auth override on the plain client -> OAuth2 dependency rejects.
    assert client.post("/api/stocks/watchlist/AAPL").status_code == 401


# --------------------------------------------------------------------------- #
# /portfolio buy + info
# --------------------------------------------------------------------------- #
def test_buy_stock_success_and_cash_deduction(auth_client, db_session):
    _add_stock(db_session, ticker="AAPL", price=100.0)
    resp = auth_client.post(
        "/api/stocks/portfolio/buy", json={"ticker": "aapl", "quantity": 2}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["cash_balance"] == pytest.approx(10_000_000.0 - 200.0)

    holding = (
        db_session.query(models.Portfolio)
        .filter_by(user_id=auth_client.test_user.id, ticker="AAPL")
        .first()
    )
    assert holding.quantity == 2
    assert holding.average_price == pytest.approx(100.0)


def test_buy_stock_unknown_ticker_404(auth_client):
    resp = auth_client.post(
        "/api/stocks/portfolio/buy", json={"ticker": "NOPE", "quantity": 1}
    )
    assert resp.status_code == 404


def test_buy_stock_insufficient_funds(auth_client, db_session):
    _add_stock(db_session, ticker="AAPL", price=100.0)
    auth_client.test_user.cash_balance = 50.0
    db_session.commit()
    resp = auth_client.post(
        "/api/stocks/portfolio/buy", json={"ticker": "AAPL", "quantity": 1}
    )
    assert resp.status_code == 400
    assert "부족" in resp.json()["detail"]


def test_buy_stock_averages_price_on_repeat_purchase(auth_client, db_session):
    stock = _add_stock(db_session, ticker="AAPL", price=100.0)
    auth_client.post("/api/stocks/portfolio/buy", json={"ticker": "AAPL", "quantity": 1})
    # Price moves up, buy again -> average of 100 and 200 over 2 shares = 150.
    stock.current_price = 200.0
    db_session.commit()
    auth_client.post("/api/stocks/portfolio/buy", json={"ticker": "AAPL", "quantity": 1})

    holding = (
        db_session.query(models.Portfolio)
        .filter_by(user_id=auth_client.test_user.id, ticker="AAPL")
        .first()
    )
    assert holding.quantity == 2
    assert holding.average_price == pytest.approx(150.0)


def test_buy_stock_rejects_non_positive_quantity(auth_client, db_session):
    _add_stock(db_session, ticker="AAPL", price=100.0)
    resp = auth_client.post(
        "/api/stocks/portfolio/buy", json={"ticker": "AAPL", "quantity": 0}
    )
    assert resp.status_code == 422  # pydantic validation (gt=0)


def test_portfolio_info_profit_loss_rate(auth_client, db_session):
    _add_stock(db_session, ticker="AAPL", price=150.0)
    db_session.add(
        models.Portfolio(
            user_id=auth_client.test_user.id,
            ticker="AAPL",
            quantity=10,
            average_price=100.0,
        )
    )
    db_session.commit()

    resp = auth_client.get("/api/stocks/portfolio/info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cash_balance"] == pytest.approx(auth_client.test_user.cash_balance)
    holding = body["holdings"][0]
    # bought @100, now @150 -> +50%
    assert holding["profit_loss_rate"] == pytest.approx(50.0)


# --------------------------------------------------------------------------- #
# /integrated/{ticker}
# --------------------------------------------------------------------------- #
def test_integrated_existing_stock_skips_external_fetch(client, db_session):
    _add_stock(db_session, ticker="AAPL", price=150.0, high=200.0, low=100.0)
    today = date.today()
    db_session.add(
        models.StockHistory(
            ticker="AAPL",
            list_date=today,
            open_price=140.0,
            high_price=155.0,
            low_price=135.0,
            close_price=150.0,
            volume=1234,
        )
    )
    db_session.commit()

    with patch("app.stocks.router.yf.Ticker") as mock_ticker:
        resp = client.get("/api/stocks/integrated/aapl")
        mock_ticker.assert_not_called()  # existing stock -> no yfinance call

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["ticker"] == "AAPL"
    assert body["score"] == 50  # (150-100)/(200-100) -> 50
    assert body["risk_level"] == "보통 (적정가)"
    assert len(body["history"]) == 1

    # a search-history row is logged for the request
    logs = db_session.query(models.SearchHistory).filter_by(ticker="AAPL").all()
    assert len(logs) == 1


def test_integrated_new_ticker_fetches_from_yfinance(client, db_session):
    empty_df = MagicMock()
    empty_df.empty = True

    fake_ticker = MagicMock()
    fake_ticker.info = {
        "currentPrice": 300.0,
        "shortName": "Newco",
        "marketCap": 5_000_000,
        "fiftyTwoWeekHigh": 350.0,
        "fiftyTwoWeekLow": 250.0,
    }
    fake_ticker.history.return_value = empty_df

    with patch("app.stocks.router.yf.Ticker", return_value=fake_ticker) as mock_ticker:
        resp = client.get("/api/stocks/integrated/NEW")
        mock_ticker.assert_called_once()

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "Newco"
    assert body["data"]["current_price"] == 300.0

    created = db_session.query(models.Stock).filter_by(ticker="NEW").first()
    assert created is not None
    assert created.high_52week == 350.0


def test_integrated_unknown_ticker_returns_404(client, db_session):
    fake_ticker = MagicMock()
    fake_ticker.info = {}  # no price keys -> treated as non-existent
    with patch("app.stocks.router.yf.Ticker", return_value=fake_ticker):
        resp = client.get("/api/stocks/integrated/GHOST")
    assert resp.status_code == 404

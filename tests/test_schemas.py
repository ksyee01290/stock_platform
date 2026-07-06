"""Unit tests for the pydantic schemas in app.stocks.schemas."""
import pytest
from pydantic import ValidationError

from app.stocks import schemas


def test_trade_request_valid():
    req = schemas.TradeRequest(ticker="AAPL", quantity=5)
    assert req.ticker == "AAPL"
    assert req.quantity == 5


@pytest.mark.parametrize("quantity", [0, -1, -100])
def test_trade_request_rejects_non_positive_quantity(quantity):
    with pytest.raises(ValidationError):
        schemas.TradeRequest(ticker="AAPL", quantity=quantity)


def test_user_create_requires_fields():
    with pytest.raises(ValidationError):
        schemas.UserCreate(username="only-username")


def test_token_schema():
    token = schemas.Token(access_token="abc", token_type="bearer")
    assert token.access_token == "abc"
    assert token.token_type == "bearer"


def test_stock_history_response_optional_ratios():
    resp = schemas.StockHistoryResponse(
        list_date="2024-01-02",
        open_price=1.0,
        high_price=2.0,
        low_price=0.5,
        close_price=1.5,
        volume=1000,
        per=None,
        pbr=None,
    )
    assert resp.per is None
    assert resp.volume == 1000


def test_watchlist_toggle_response():
    resp = schemas.WatchlistToggleResponse(
        ticker="AAPL", is_favorite=True, message="added"
    )
    assert resp.is_favorite is True


def test_from_attributes_config_on_user_response():
    class FakeUser:
        id = 7
        username = "obj-user"

    resp = schemas.UserResponse.model_validate(FakeUser())
    assert resp.id == 7
    assert resp.username == "obj-user"

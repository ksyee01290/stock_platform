"""Unit tests for the background batch engine app.tasks.stock_tasks."""
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.stocks import models
from app.tasks import stock_tasks


@pytest.fixture()
def patched_session(db_session):
    """Make SessionLocal in the tasks module return our test session.

    db.close() (called in the batch's finally block) does not destroy the
    session object, so we can still query it afterwards for assertions.
    """
    with patch.object(stock_tasks, "SessionLocal", return_value=db_session):
        yield db_session


def _year_history_df():
    idx = pd.to_datetime(["2024-01-02", "2024-01-03"])
    return pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [12.0, 13.0],
            "Low": [9.0, 10.0],
            "Close": [11.0, 12.0],
            "Volume": [1000, 2000],
        },
        index=idx,
    )


def test_batch_no_stocks_is_noop(patched_session):
    with patch.object(stock_tasks.yf, "Ticker") as mock_ticker:
        stock_tasks.update_top_stocks_batch()
    mock_ticker.assert_not_called()


def test_batch_seeds_history_and_updates_price(patched_session):
    db = patched_session
    db.add(models.Stock(ticker="AAPL", name="Apple", current_price=100.0))
    db.commit()

    fake = MagicMock()
    fake.history.return_value = _year_history_df()
    fake.info = {
        "currentPrice": 175.0,
        "shortName": "Apple Inc",
        "marketCap": 9_000_000,
        "fiftyTwoWeekHigh": 200.0,
        "fiftyTwoWeekLow": 120.0,
        "open": 170.0,
        "dayHigh": 178.0,
        "dayLow": 168.0,
        "volume": 555,
    }

    with patch.object(stock_tasks.yf, "Ticker", return_value=fake):
        stock_tasks.update_top_stocks_batch()

    updated = db.query(models.Stock).filter_by(ticker="AAPL").first()
    assert updated.current_price == 175.0
    assert updated.name == "Apple Inc"
    assert updated.high_52week == 200.0

    # Seeded rows from the 1y frame plus a live snapshot row for today.
    history = db.query(models.StockHistory).filter_by(ticker="AAPL").all()
    assert len(history) >= 3
    from datetime import date

    assert any(h.list_date == date.today() for h in history)


def test_batch_skips_seeding_when_history_exists(patched_session):
    db = patched_session
    db.add(models.Stock(ticker="AAPL", name="Apple", current_price=100.0))
    db.add(
        models.StockHistory(
            ticker="AAPL",
            list_date=pd.Timestamp("2023-06-01").date(),
            open_price=1.0,
            high_price=2.0,
            low_price=0.5,
            close_price=1.5,
            volume=10,
        )
    )
    db.commit()

    fake = MagicMock()
    fake.info = {"currentPrice": 150.0}

    with patch.object(stock_tasks.yf, "Ticker", return_value=fake):
        stock_tasks.update_top_stocks_batch()

    fake.history.assert_not_called()
    assert db.query(models.Stock).filter_by(ticker="AAPL").first().current_price == 150.0


def test_batch_skips_stock_with_empty_info(patched_session):
    db = patched_session
    db.add(models.Stock(ticker="AAPL", name="Apple", current_price=100.0))
    db.add(
        models.StockHistory(
            ticker="AAPL",
            list_date=pd.Timestamp("2023-06-01").date(),
            open_price=1.0,
            high_price=2.0,
            low_price=0.5,
            close_price=1.5,
            volume=10,
        )
    )
    db.commit()

    fake = MagicMock()
    fake.info = {}  # falsy -> stock is skipped, price unchanged

    with patch.object(stock_tasks.yf, "Ticker", return_value=fake):
        stock_tasks.update_top_stocks_batch()

    assert db.query(models.Stock).filter_by(ticker="AAPL").first().current_price == 100.0


def test_batch_continues_on_individual_ticker_error(patched_session):
    db = patched_session
    db.add(models.Stock(ticker="BAD", name="Bad", current_price=1.0))
    db.commit()

    with patch.object(stock_tasks.yf, "Ticker", side_effect=RuntimeError("boom")):
        # Must not raise; the per-item try/except swallows the error.
        stock_tasks.update_top_stocks_batch()

    # Stock still present, untouched.
    assert db.query(models.Stock).filter_by(ticker="BAD").first().current_price == 1.0


def test_start_scheduler_registers_job_and_starts():
    with patch.object(stock_tasks, "scheduler") as mock_sched:
        stock_tasks.start_scheduler()
    mock_sched.add_job.assert_called_once()
    _, kwargs = mock_sched.add_job.call_args
    assert kwargs.get("id") == "sync_stocks_job"
    mock_sched.start.assert_called_once()


def test_shutdown_scheduler_shuts_down():
    with patch.object(stock_tasks, "scheduler") as mock_sched:
        stock_tasks.shutdown_scheduler()
    mock_sched.shutdown.assert_called_once()

"""Unit test for the get_db dependency generator in app.database."""
from unittest.mock import MagicMock, patch

from app import database


def test_get_db_yields_session_and_closes():
    fake_session = MagicMock()
    with patch.object(database, "SessionLocal", return_value=fake_session):
        gen = database.get_db()
        yielded = next(gen)
        assert yielded is fake_session
        fake_session.close.assert_not_called()
        # Exhausting the generator triggers the finally: close().
        gen.close()
        fake_session.close.assert_called_once()

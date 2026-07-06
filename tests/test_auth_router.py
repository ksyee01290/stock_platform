"""Endpoint + dependency tests for app.auth.router (signup / login / get_current_user)."""
import jwt
import pytest
from fastapi import HTTPException

from app.auth.router import get_current_user
from app.core import security
from app.stocks import models


def test_signup_creates_user(client, db_session):
    resp = client.post(
        "/api/auth/signup", json={"username": "alice", "password": "pw12345"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert "id" in body
    assert "password" not in body  # hashed password must not leak

    stored = db_session.query(models.User).filter_by(username="alice").first()
    assert stored is not None
    assert stored.hashed_password != "pw12345"


def test_signup_duplicate_username_rejected(client):
    payload = {"username": "bob", "password": "pw12345"}
    assert client.post("/api/auth/signup", json=payload).status_code == 201
    dup = client.post("/api/auth/signup", json=payload)
    assert dup.status_code == 400
    assert "이미 존재" in dup.json()["detail"]


def test_login_success_returns_bearer_token(client):
    client.post("/api/auth/signup", json={"username": "carol", "password": "pw12345"})
    resp = client.post(
        "/api/auth/login", json={"username": "carol", "password": "pw12345"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    payload = jwt.decode(
        body["access_token"], security.SECRET_KEY, algorithms=[security.ALGORITHM]
    )
    assert "sub" in payload


def test_login_unknown_user(client):
    resp = client.post(
        "/api/auth/login", json={"username": "ghost", "password": "whatever"}
    )
    assert resp.status_code == 400


def test_login_wrong_password(client):
    client.post("/api/auth/signup", json={"username": "dave", "password": "pw12345"})
    resp = client.post(
        "/api/auth/login", json={"username": "dave", "password": "WRONG"}
    )
    assert resp.status_code == 400


def test_get_current_user_valid_token(db_session, make_user):
    user = make_user(username="edith")
    token = security.create_access_token({"sub": str(user.id)})
    resolved = get_current_user(token=token, db=db_session)
    assert resolved.id == user.id


def test_get_current_user_invalid_token(db_session):
    with pytest.raises(HTTPException) as exc:
        get_current_user(token="not-a-jwt", db=db_session)
    assert exc.value.status_code == 401


def test_get_current_user_token_without_sub(db_session):
    token = security.create_access_token({"foo": "bar"})
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 401


def test_get_current_user_nonexistent_user(db_session):
    token = security.create_access_token({"sub": "99999"})
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 401

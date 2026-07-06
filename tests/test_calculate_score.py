"""Unit tests for the pure scoring helper app.stocks.router.calculate_stock_score."""
import pytest

from app.stocks.router import calculate_stock_score


@pytest.mark.parametrize("high, low", [(None, 50), (100, None), (0, 0), (100, 100)])
def test_missing_or_equal_bounds_returns_unknown(high, low):
    score, risk, comment = calculate_stock_score(75, high, low)
    assert score == 50
    assert risk == "판단 불가"
    assert "데이터 부족" in comment


def test_score_at_low_is_zero_and_safe():
    score, risk, _ = calculate_stock_score(100, 200, 100)
    assert score == 0
    assert risk == "안전 (바닥권)"


def test_score_at_high_is_hundred_and_risky():
    score, risk, _ = calculate_stock_score(200, 200, 100)
    assert score == 100
    assert risk == "위험 (고점 과열)"


def test_score_midpoint_is_normal():
    score, risk, _ = calculate_stock_score(150, 200, 100)
    assert score == 50
    assert risk == "보통 (적정가)"


@pytest.mark.parametrize(
    "current, expected_score, expected_risk",
    [
        (130, 30, "안전 (바닥권)"),   # boundary: <= 30 is safe
        (131, 31, "보통 (적정가)"),   # just above safe band
        (170, 70, "보통 (적정가)"),   # boundary: <= 70 is normal
        (171, 71, "위험 (고점 과열)"),  # just above normal band
    ],
)
def test_band_boundaries(current, expected_score, expected_risk):
    score, risk, _ = calculate_stock_score(current, 200, 100)
    assert score == expected_score
    assert risk == expected_risk


def test_comment_includes_score():
    score, _, comment = calculate_stock_score(150, 200, 100)
    assert str(score) in comment


def test_non_numeric_input_is_handled_gracefully():
    """The bare except in the function should trap arithmetic/type errors."""
    score, risk, comment = calculate_stock_score("not-a-number", 200, 100)
    assert score == 50
    assert risk == "오류 발생"

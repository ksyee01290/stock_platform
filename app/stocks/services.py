"""
[주식 분석 도메인 - 공유 서비스 유틸리티]
- yfinance 데이터 가공 로직을 한곳에 모아, router와 batch task에서 재사용합니다.
"""
import math
from datetime import datetime

from app.stocks import models


def extract_live_price(info: dict, fallback: float = 0.0) -> float:
    """yfinance info dict에서 현재가를 추출합니다."""
    price = info.get("currentPrice") or info.get("regularMarketPrice") or fallback
    return float(price)


def extract_stock_name(info: dict, fallback: str = "") -> str:
    """yfinance info dict에서 종목명을 추출합니다."""
    return info.get("shortName") or info.get("longName") or fallback


def build_history_from_dataframe(
    ticker: str,
    hist_df,
    fallback_price: float = 0.0,
) -> list[models.StockHistory]:
    """
    yfinance history DataFrame을 StockHistory 모델 객체 리스트로 변환합니다.
    NaN 값은 fallback_price로 대체합니다.
    """
    if hist_df is None or hist_df.empty:
        return []

    history_items: list[models.StockHistory] = []
    for index, row in hist_df.iterrows():
        list_date = index.date() if hasattr(index, "date") else index

        def _safe_price(key: str) -> float:
            val = row.get(key)
            if val is None or math.isnan(float(val)):
                return float(fallback_price)
            return float(val)

        history_items.append(
            models.StockHistory(
                ticker=ticker,
                list_date=list_date,
                open_price=_safe_price("Open"),
                high_price=_safe_price("High"),
                low_price=_safe_price("Low"),
                close_price=_safe_price("Close"),
                volume=int(row.get("Volume") or 0),
            )
        )

    return history_items


def update_stock_fields(stock: models.Stock, info: dict) -> None:
    """yfinance info dict의 값으로 Stock 모델 필드를 갱신합니다."""
    stock.name = extract_stock_name(info, fallback=stock.name)
    stock.current_price = extract_live_price(info, fallback=stock.current_price)
    stock.market_cap = info.get("marketCap") or stock.market_cap
    stock.high_52week = info.get("fiftyTwoWeekHigh") or stock.high_52week
    stock.low_52week = info.get("fiftyTwoWeekLow") or stock.low_52week
    stock.updated_at = datetime.now()

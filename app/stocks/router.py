"""
[주식 분석 도메인 - 엔드포인트 라우터]
- Frontend(React/Next.js)의 API 요청을 수신하는 문지기 역할을 합니다.
- 3단계 하이브리드 데이터 관리 정책(DB 캐싱 + 5초 방어막 + 실시간 가격 패치)의 전체 흐름을 제어합니다.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta, timezone
from typing import List
from pydantic import BaseModel

import yfinance as yf
import threading

from app.stocks import models
from app.database import get_db

router = APIRouter()

stock_lock = threading.Lock()

class StockHistoryResponse(BaseModel):
    list_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    per: float | None
    pbr: float | None
    
    class Config:
        from_attributes = True
        
class IntegratedStockResponse(BaseModel):
    status: str
    message: str
    data: dict
    score: int
    risk_level: str
    comment: str
    history: List[StockHistoryResponse]


def calculate_stock_score(current_price, high_52week, low_52week):
    try:
        if not high_52week or not low_52week or high_52week == low_52week:
            return 50, "판단 불가", "데이터 부족으로 주가 위치를 분석할 수 없음"
        
        score = round(((current_price - low_52week) / (high_52week - low_52week)) * 100)
        
        if score <= 30:
            return score, "안전 (바닥권)", f"현재 주가는 52주 최저가 부근({score}점)으로, 상대적으로 저평가된 매력적인 구간입니다."
        elif score <= 70:
            return score, "보통 (적정가)", f"현재 주가는 중간 지점({score}점)에 위치해 있으며, 시장의 평균적인 흐름을 따르고 있습니다."
        else:
            return score, "위험 (고점 과열)", f"현재 주가가 52주 최고가에 근접({score}점)했습니다. 고점 과열 상태일 수 있으니 유의하세요."
    except:
        return 50, "오류 발생", "점수 연산 중 문제가 발생했습니다."
    

@router.get("/integrated/{ticker}", response_model=IntegratedStockResponse)
def get_stock_history(ticker: str, db: Session = Depends(get_db)):
    ticker = ticker.upper() # 대문자 변환 (aapl -> AAPL)
    
    today = date.today()
    one_year_ago = today - timedelta(days=365)
    
    # [선행 조회] 1년 치 차트 데이터 조회
    history_data = db.query(models.StockHistory)\
        .filter(models.StockHistory.ticker == ticker)\
        .filter(models.StockHistory.list_date >= one_year_ago)\
        .order_by(models.StockHistory.list_date.asc())\
        .all()   
    
    # 💡 [핵심 수리] db.rollback()으로 데이터가 만료되기 전에 순수 Pydantic 모델 리스트로 복사본을 박제합니다.
    # 이렇게 하면 연타를 쳐서 아래에서 어떤 세션 조작이 일어나도 history 데이터가 완벽하게 보존됩니다.
    safe_history = [StockHistoryResponse.from_orm(h) for h in history_data]
    
    with stock_lock:
        db.rollback()
        
        existing_stock = db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
        
        if existing_stock:    
            current_time = datetime.now(timezone.utc)
            stock_updated_time = existing_stock.updated_at
            
            if stock_updated_time.tzinfo is None:
                stock_updated_time = stock_updated_time.replace(tzinfo=timezone.utc)
                
            time_difference = current_time - stock_updated_time
            

            # [1단계] 연타 방어막 작동 구역
            if time_difference < timedelta(seconds=5):
                print(f"[방어막 작동] {ticker} 요청이 너무 단시간에 반복되어 캐싱된 데이터를 반환합니다.")
                score, risk, comment = calculate_stock_score(existing_stock.current_price, existing_stock.high_52week, existing_stock.low_52week)
                
                return {
                    "status": "성공 (방어막 캐싱)",
                    "message": "디도스 방지를 위해 5초 이내 반복 요청은 저장된 데이터를 반환합니다.", # massage -> message 오타 수정
                    "data": {
                        "id": existing_stock.id,
                        "ticker": ticker, # 프론트엔드가 요구하는 ticker 매핑 추가
                        "name": existing_stock.name,
                        "current_price": existing_stock.current_price,
                        "market_cap": existing_stock.market_cap,
                        "high_52week": existing_stock.high_52week,
                        "low_52week": existing_stock.low_52week          
                    },
                    "score": score,
                    "risk_level": risk,
                    "comment": comment,
                    "history": safe_history # 박제된 안전한 데이터 반환          
                }
                
            # [2단계] 1시간 이내 가격만 실시간 패치 구역
            elif time_difference < timedelta(hours=1):
                print(f"[안정 구역] 1시간 이내 데이터 존재. 실시간 주가 검증 진행.")
                try:
                    live_info = yf.Ticker(ticker).info
                    live_price = live_info.get("currentPrice") or live_info.get("regularMarketPrice") or existing_stock.current_price
                    existing_stock.current_price = float(live_price)
                    db.commit()
                    db.refresh(existing_stock)
                except Exception as e:
                    print(f"[실시간 주가 패치 실패] {ticker} 실시간 가격 호출 실패, DB 값 활용: {str(e)}")
                    
                score, risk, comment = calculate_stock_score(existing_stock.current_price, existing_stock.high_52week, existing_stock.low_52week)
                
                return {
                    "status": "성공 (DB 최신 데이터)",
                    "message": f"1시간 이내에 업데이트된 데이터가 있습니다. (경과시간: {time_difference})",
                    "data": {
                        "id": existing_stock.id,
                        "ticker": ticker, # ticker 추가
                        "name": existing_stock.name,
                        "current_price": existing_stock.current_price,
                        "market_cap": existing_stock.market_cap,
                        "high_52week": existing_stock.high_52week,
                        "low_52week": existing_stock.low_52week          
                    },
                    "score": score,
                    "risk_level": risk,
                    "comment": comment,
                    "history": safe_history
                }
        
        # [3단계] DB에 데이터가 없거나 1시간이 지난 경우 실시간 데이터 수집
        try:
            stock_info = yf.Ticker(ticker).info
            
            if "regularMarketPrice" not in stock_info and "currentPrice" not in stock_info:
                raise HTTPException(status_code=404, detail="존재하지 않는 주식 이거나 데이터를 가져올 수 없습니다.")
            
            current_price = stock_info.get("currentPrice") or stock_info.get("regularMarketPrice") or 0.0
            
            if existing_stock:
                existing_stock.name = stock_info.get("shortName") or stock_info.get("longName") or ticker
                existing_stock.current_price = float(current_price)
                existing_stock.market_cap = stock_info.get("marketCap")
                existing_stock.high_52week = stock_info.get("fiftyTwoWeekHigh")
                existing_stock.low_52week = stock_info.get("fiftyTwoWeekLow")
                
                db.commit()
                db.refresh(existing_stock)
                
                score, risk, comment = calculate_stock_score(existing_stock.current_price, existing_stock.high_52week, existing_stock.low_52week)
                
                return {
                    "status": "성공 (DB 업데이트 완료)",
                    "message": f"오래된 {ticker} 데이터를 새로 갱신했습니다.",
                    "data": {
                        "id": existing_stock.id,
                        "ticker": ticker,
                        "name": existing_stock.name,
                        "current_price": existing_stock.current_price,
                        "market_cap": existing_stock.market_cap,
                        "high_52week": existing_stock.high_52week,
                        "low_52week": existing_stock.low_52week          
                    },
                    "score": score,
                    "risk_level": risk,
                    "comment": comment,
                    "history": safe_history
                }
            else:
                new_stock = models.Stock(
                    ticker=ticker,
                    name=stock_info.get("shortName") or stock_info.get("longName") or ticker,
                    current_price = float(current_price),
                    market_cap=stock_info.get("marketCap"),
                    high_52week=stock_info.get("fiftyTwoWeekHigh"),
                    low_52week=stock_info.get("fiftyTwoWeekLow")
                )

                db.add(new_stock)
                db.commit()
                db.refresh(new_stock)

                score, risk, comment = calculate_stock_score(new_stock.current_price, new_stock.high_52week, new_stock.low_52week)
                
                return {
                    "status": "성공 (실시간 수집)",
                    "message": f"yfinance에서 {ticker} 데이터를 실시간으로 가져와 DB에 저장했습니다.",
                    "data": {
                        "id": new_stock.id, # existing_stock -> new_stock 변수 오타 전면 수정
                        "ticker": ticker,
                        "name": new_stock.name,
                        "current_price": new_stock.current_price,
                        "market_cap": new_stock.market_cap,
                        "high_52week": new_stock.high_52week,
                        "low_52week": new_stock.low_52week          
                    },
                    "score": score,
                    "risk_level": risk,
                    "comment": comment,
                    "history": safe_history
                }
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"주식 데이터 수집 중 오류 발생: {str(e)}")
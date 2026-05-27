from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone # 시간계산 라이브러리
import yfinance as yf

from app.stocks import models
from app.database import get_db

router = APIRouter()

# 주소뒤에 {ticker}을 붙여서 어떤주식이든 검색할수있음
@router.get("/analysis/{ticker}")
def get_stock_analysis(ticker: str, db:Session = Depends(get_db)):
    ticker = ticker.upper() # 대문자변환 (aapl -> AAPL)
    
    #[1단계] DB에 주식이 이미 저장되어 있는지 조회
    existing_stock = db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
    
    #[2단계] DB에 데이터 존재하면 유효시간(1시간) 체크
    if existing_stock:
        
        # 시간 계산 에러방지 utc타임존
        current_time = datetime.now(timezone.utc)
        stock_updated_time = existing_stock.updated_at
        
        if stock_updated_time.tzinfo is None:
            stock_updated_time = stock_updated_time.replace(tzinfo=timezone.utc)
            
        time_difference = current_time - stock_updated_time
        
        if time_difference < timedelta(hours=1): 
            return {
                "status": "성공 (DB 최신 데이터)",
                "message": f"1시간 이내에 업데이트된 데이터가 있습니다. (경과시간: {time_difference})",
                "data": existing_stock
            }
        else:
            print(f"{ticker} 데이터가 1시간 이상 지났습니다. 업데이트를 진행합니다.")
    
    #[3단계] DB에 데이터가 없거나 1시간이 지난 경우 실시간 데이터수집
    try:
        stock_info = yf.Ticker(ticker).info
        
        # yfinance 에서 정상적이 데이터를 가져오지못한경우 대처
        if "regularMarketPrice" not in stock_info and "currentPrice" not in stock_info:
            raise HTTPException(status_code=404, detail="존재하지 않는 주식 이거나 데이터를 가져올수 없습니다.")
        
        current_price = stock_info.get("currentPrice") or stock_info.get("regularMarketPrice") or 0.0
        
        if existing_stock:
            existing_stock.name = stock_info.get("shortName") or stock_info.get("longName") or ticker
            existing_stock.current_price = float(current_price)
            existing_stock.market_cap = stock_info.get("marketCap")
            existing_stock.high_52week = stock_info.get("fiftyTwoWeekHigh")
            existing_stock.low_52week = stock_info.get("fiftyTwoWeekLow")
            
            db.commit()
            db.refresh(existing_stock)
            
            return {
                "status": "성공 (DB 업데이트 완료)",
                "message": f"오래된 {ticker} 데이터를 새로 갱신했습니다.",
                "data": existing_stock
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
        
            return{
                "status": "성공 (실시간 수집)",
                "message": f"yfinance에서 {ticker} 데이터를 실시간으로 가져와 DB에 저장했습니다.",
                "data": new_stock
            }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"주식 데이터 수집 중 오류 발생: {str(e)}")
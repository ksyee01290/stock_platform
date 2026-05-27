from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
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
    
    #[2단계] DB에 이미 있으면 반환역할
    if existing_stock:
        return {
            "status": "성공 (DB 조회)",
            "message": "데이터베이스에 이미 저장된 주식 정보를 가져왔습니다.",
            "data": existing_stock
        }
    
    #[3단계] DB에 없다면, yfinance를 사용 실시간 데이터 가져옴
    try:
        stock_info = yf.Ticker(ticker).info
        
        # yfinance 에서 정상적이 데이터를 가져오지못한경우 대처
        if "regularMarketPrice" not in stock_info and "currentPrice" not in stock_info:
            raise HTTPException(status_code=404, detail="존재하지 않는 주식 이거나 데이터를 가져올수 없습니다.")
        
        # 안전하게 추출
        current_price = stock_info.get("currentPrice") or stock_info.get("regularMarketPrice") or 0.0
        
        # yfinance 에서 긁어온 데이터로 DB 모델 객체 생성
        new_stock = models.Stock(
            ticker=ticker,
            name=stock_info.get("shortName") or stock_info.get("longName") or ticker,
            current_price = float(current_price),
            market_cap=stock_info.get("marketCap"),
            high_52week=stock_info.get("fiftyTwoWeekHigh"),
            low_52week=stock_info.get("fiftyTwoWeekLow")
        )
        
        #[4단계] DB에 데이터 저장
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
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone # 시간계산 라이브러리
import yfinance as yf

from app.stocks import models
from app.database import get_db

router = APIRouter()

def calculate_stock_score(current_price, high_52week, low_52week):
    try:
        if not high_52week or not low_52week or high_52week == low_52week:
            return 50, "판단 불가", "데이터 부족으로 주가 위치를 분석할수 없음"
        
        score = round(((current_price - low_52week) / (high_52week - low_52week)) * 100)
        
        if score <= 30:
            return score, "안전 (바닥권)", f"현재 주가는 52주 최저가 부근({score}점)으로, 상대적으로 저평가된 매력적인 구간입니다."
        elif score <= 70:
            return score, "보통 (적정가)", f"현재 주가는 중간 지점({score}점)에 위치해 있으며, 시장의 평균적인 흐름을 따르고 있습니다."
        else:
            return score, "위험 (고점 과열)", f"현재 주가가 52주 최고가에 근접({score}점)했습니다. 고점 과열 상태일 수 있으니 유의하세요."
    except:
        return 50, "오류 발생", "점수 연산 중 문제가 발생했습니다."

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
            score, risk, comment = calculate_stock_score(existing_stock.current_price, existing_stock.high_52week, existing_stock.low_52week)
            return {
                "status": "성공 (DB 최신 데이터)",
                "message": f"1시간 이내에 업데이트된 데이터가 있습니다. (경과시간: {time_difference})",
                "data": existing_stock,
                "score": score,
                "risk_level": risk,
                "comment": comment
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
            
            score, risk, comment = calculate_stock_score(existing_stock.current_price, existing_stock.high_52week, existing_stock.low_52week)
            return {
                "status": "성공 (DB 업데이트 완료)",
                "message": f"오래된 {ticker} 데이터를 새로 갱신했습니다.",
                "data": existing_stock,
                "score": score,
                "risk_level": risk,
                "comment": comment
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
            return{
                "status": "성공 (실시간 수집)",
                "message": f"yfinance에서 {ticker} 데이터를 실시간으로 가져와 DB에 저장했습니다.",
                "data": new_stock,
                "score": score,
                "risk_level": risk,
                "comment": comment
            }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"주식 데이터 수집 중 오류 발생: {str(e)}")
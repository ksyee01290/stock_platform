from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
import yfinance as yf
from datetime import datetime

from app.database import SessionLocal
from app.stocks import models

def update_top_stocks_batch():
    """
    DB에 등록된 주식들의 무거운 지표들을 주기적으로 자동갱신. 
    """
    db: Session = SessionLocal()
    try:
        stocks = db.query(models.Stock).all()
        if not stocks:
            print("[Batch] 현재 DB에 등록된 주식이 없어 배치를 건너뜁니다.")
            return
        
        print(f"[Batch] 총{len(stocks)}개 종목 배치 갱신 시작: {datetime.now()}")
        
        for stock in stocks:
            try:
                ticker_data = yf.Ticker(stock.ticker)
                info = ticker_data.info
                
                stock.name= info.get("shortName") or info.get("longName") or stock.name
                stock.market_cap = info.get("marketCap") or stock.market_cap
                stock.high_52week = info.get("fiftyTwoWeekHigh") or stock.high_52week
                stock.low_52week = info.get("fiftyTwoWeekLow") or stock.low_52week
                
                stock.updated_at = datetime.utcnow()
                
                print(f"[Batch] {stock.ticker} 기본 정보 갱신 완료")
            except Exception as item_error:
                print(f"[Batch] {stock.ticker} 갱신 중 개별 오류 발생: {str(item_error)}")
                continue
            
        db.commit()
        print("[Batch] 모든 종목 배치 갱신 완료 및 DB 저장 성공")
        
    except Exception as e:
        db.rollback()
        print(f"[Batch] 시스템 치명적 오류 발생: {str(e)}")
        
    finally:
        db.close()
        
scheduler = BackgroundScheduler()

def start_scheduler():
    scheduler.add_job(update_top_stocks_batch, 'interval', minutes=1, id='sync_stocks_job')
    scheduler.start()
    print("[Scheduler] 백그라운드 주식 배치 스케줄러가 성공적으로 시작되었습니다.")

def shutdown_scheduler():
    scheduler.shutdown()
    print("[Scheduler] 스케줄러가 안전하게 종료되었습니다.")
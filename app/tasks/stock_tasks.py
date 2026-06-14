"""
[주식 분석 도메인 - 백그라운드 배치]
- 유저 요청과 무관하게 뒤에서 10분마다 자동으로 호출.
- [변경사항] 기본 정보뿐 아니라 현재가(current_price)를 동기화하고, 차트용 stockhistory 스냅샷을 주기적으로 누적
"""
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
import yfinance as yf
from datetime import datetime, timezone

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
                
                if not info:
                    print(f"[Batch] {stock.ticker} 데이터를 가져오지 못해 건너뜁니다.")
                    continue
                
                live_price = info.get("currentPrice") or info.get("regularMarketPrice") or stock.current_price
                
                stock.name= info.get("shortName") or info.get("longName") or stock.name
                stock.current_price = float(live_price)
                stock.market_cap = info.get("marketCap") or stock.market_cap
                stock.high_52week = info.get("fiftyTwoWeekHigh") or stock.high_52week
                stock.low_52week = info.get("fiftyTwoWeekLow") or stock.low_52week
                stock.updated_at = datetime.now()
                
                history_entry = models.StockHistory(
                    ticker=stock.ticker,
                    list_date=datetime.now().date(),
                    open_price=float(info.get("open") or live_price),
                    high_price=float(info.get("dayHigh") or live_price),
                    low_price=float(info.get("dayLow") or live_price),
                    close_price=float(live_price),   # 현재 시점의 종가는 라이브 가격
                    volume=int(info.get("volume") or 0)
                )
                db.add(history_entry)
                
                print(f"[Batch] {stock.ticker} 정보 갱신 및 10분 단위 스냅샷({live_price}원) 적재 완료")
                
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
    scheduler.add_job(update_top_stocks_batch, 'interval', minutes=10, id='sync_stocks_job')
    # scheduler.add_job(update_top_stocks_batch, 'cron', hour=7, minute=0, id='sync_stocks_job')
    
    scheduler.start()
    
    print("[Scheduler] 백그라운드 주식 배치 스케줄러가 성공적으로 시작되었습니다.")
    # print("[Scheduler] 매일 아침 7시 정기 배치를 위한 크론 스케줄러 시동")

def shutdown_scheduler():
    scheduler.shutdown()
    print("[Scheduler] 스케줄러가 안전하게 종료되었습니다.")
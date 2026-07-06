"""
[주식 분석 도메인 - 백그라운드 배치]
- 유저 요청과 무관하게 뒤에서 10분마다 자동으로 호출.
- [변경사항] 기본 정보뿐 아니라 현재가(current_price)를 동기화하고, 차트용 stockhistory 스냅샷을 주기적으로 누적
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
import yfinance as yf
from datetime import datetime

from app.database import SessionLocal
from app.stocks import models

logger = logging.getLogger(__name__)

def update_top_stocks_batch():
    """
    DB에 등록된 주식들의 과거 1년치 데이터 초기 적재 및 10분 주기 실시간 가격 갱신 
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
                # ---------------------------------------------------------------------
                # [핵심 보충] 과거 데이터 초기 적재 (Data Seeding)
                # StockHistory 테이블에 해당 종목의 과거 데이터가 한 건도 없다면 1년 치를 통째로 긁어옵니다.
                # ---------------------------------------------------------------------
                history_exists = db.query(models.StockHistory).filter(models.StockHistory.ticker == stock.ticker).first()
                if not history_exists:
                    print(f"[Initial Seed] {stock.ticker} 종목의 과거 1년치 일봉 데이터를 수집합니다...")
                    hist_df = ticker_data.history(period="1y")
                    
                    if hist_df is not None and not hist_df.empty:
                        history_items = []
                        for index, row in hist_df.iterrows():
                            list_date = index.date() if hasattr(index, 'date') else index

                            history_entry = models.StockHistory(
                                ticker=stock.ticker,
                                list_date=list_date,
                                open_price=float(row.get('Open') or 0.0),
                                high_price=float(row.get('High') or 0.0),
                                low_price=float(row.get('Low') or 0.0),
                                close_price=float(row.get('Close') or 0.0),
                                volume=int(row.get('Volume') or 0)
                            )
                            history_items.append(history_entry)

                        if history_items:
                            db.bulk_save_objects(history_items)
                            logger.info("[Initial Seed] %s 과거 데이터 %d건 적재", stock.ticker, len(history_items))
                                
                                
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
                
            except Exception:
                logger.exception("[Batch] %s 갱신 중 개별 오류 발생", stock.ticker)
                continue
            
        db.commit()
        print("[Batch] 모든 종목 배치 갱신 완료 및 DB 저장 성공")
        
    except Exception:
        db.rollback()
        logger.exception("[Batch] 시스템 치명적 오류 발생")

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
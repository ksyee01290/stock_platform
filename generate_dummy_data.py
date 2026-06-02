"""
[대용량 시계열 데이터 벌크 적재 스크립트]
- 5개 핵심 종목의 10년 치(약 12,000건) 일별 가짜 주가 데이터를 생성
- SQLAlchemy의 bulk_insert_mappings를 활용하여 단 몇 초 만에 PostgreSQL에 적재
"""
import random
from datetime import datetime, timedelta, date
from app.database import SessionLocal, engine
from app.stocks import models

# 테스트용 기본 주식 데이터
DUMMY_STOCKS = [
    {"ticker": "005930.KS", "name": "삼성전자", "current_price": 75000.0, "market_cap": 450000000000000, "high_52week": 85000.0, "low_52week": 65000.0},
    {"ticker": "000660.KS", "name": "SK하이닉스", "current_price": 180000.0, "market_cap": 130000000000000, "high_52week": 200000.0, "low_52week": 120000.0},
    {"ticker": "AAPL", "name": "애플", "current_price": 180.0, "market_cap": 2800000000000, "high_52week": 200.0, "low_52week": 165.0},
    {"ticker": "NVDA", "name": "엔비디아", "current_price": 900.0, "market_cap": 2200000000000, "high_52week": 970.0, "low_52week": 400.0},
    {"ticker": "AXP", "name": "아메리칸 익스프레스", "current_price": 220.0, "market_cap": 160000000000, "high_52week": 240.0, "low_52week": 170.0},
]

def generate_data():
    db = SessionLocal()
    try:
        print("===== 1단계: 기본 주식 종목(stocks) 등록 시작 =====")
        for stock_data in DUMMY_STOCKS:
            existing = db.query(models.Stock).filter(models.Stock.ticker == stock_data["ticker"]).first()
            if not existing:
                new_stock = models.Stock(**stock_data)
                db.add(new_stock)
        db.commit()
        print(" 기본 주식 종목 등록 완료!")
        
        print("\n===== 2단계: 10년치 시계열 히스토리 데이터 생성 시작 =====")
        end_date = date.today()
        start_date = end_date - timedelta(days=365*10)
        
        history_mappings = []
        total_days = (end_date - start_date).days
        
        for stock in DUMMY_STOCKS:
            ticker = stock["ticker"]
            base_price = stock["current_price"]
            print(f"-> {ticker} 종목 가짜 데이터 생성중...")
            
            current_loop_date = start_date
            price_tracker = base_price * 0.5
            
            while current_loop_date <= end_date:
                if current_loop_date.weekday() >=5:
                    current_loop_date += timedelta(days=1)
                    continue
                
                # 전날 종가 기준 3% 내외로 무작위 변동
                change_percent = random.uniform(-0.03, 0.03)
                open_price = price_tracker * (1 + random.uniform(-0.01, 0.01))
                high_price = max(open_price, price_tracker) * (1 + random.uniform(0, 0.02))
                low_price = min(open_price, price_tracker) * (1 - random.uniform(0, 0.02))
                close_price = price_tracker * (1 + change_percent)
                
                # 음수 방지
                if close_price <= 0:
                    close_price = 10.0
                    
                volume = random.randint(100000, 5000000)
                
                per = round(random.uniform(8.0, 35.0), 2)
                pbr = round(random.uniform(0.8, 5.0), 2)
                
                history_mappings.append({
                    "ticker": ticker,
                    "list_date": current_loop_date,
                    "open_price": round(open_price, 2),
                    "high_price": round(high_price, 2),
                    "low_price": round(low_price, 2),
                    "close_price": round(close_price, 2),
                    "volume": volume,
                    "per": per,
                    "pbr": pbr
                })
                
                price_tracker = close_price
                current_loop_date += timedelta(days=1)
                
        print(f" 총 {len(history_mappings)}건의 시계열 데이터 매핑 완료.")
        print(f"PostgreSQL로 대량 벌크 인서트 투하중...")
        
        db.bulk_insert_mappings(models.StockHistory, history_mappings)
        db.commit()
        
        print("모든 대용량 시계열 데이터가 성공적으로 적재되었습니다.")
        
    except Exception as e:
        db.rollback()
        print(f"데이터 생성중 오류 발생: {str(e)}")
    finally:
        db.close()
        
if __name__ == "__main__":
    generate_data()
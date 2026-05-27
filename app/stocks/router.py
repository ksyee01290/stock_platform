from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.stocks import models

from app.database import get_db

router = APIRouter()

@router.get("/analysis")
def get_stock_analysis(db: Session = Depends(get_db)):
    # 테스트용 데이터
    test_stock = models.Stock(
        ticker="005930",
        name="삼성전자",
        current_price=70000.0,
        market_cap=448000000000000,
        high_52week=80000.0,
        low_52week=60000.0
    )
    
    try:
        db.add(test_stock)
        db.commit()
        db.refresh(test_stock)
        return{
            "status": "성공",
            "message": "주식 데이터를 성공적으로 DB에 저장했습니다.",
            "data": test_stock
        }
    except Exception as e:
        db.rollback()
        existing_stock = db.query(models.Stock).filter(models.Stock.ticker == "005930").first()
        return {
            "status": "성공(기존 데이터)",
            "message": "이미 존재하는 종목입니다. DB에서 기존 데이터를 가져왔습니다.",
            "data": existing_stock
        }
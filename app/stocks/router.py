from fastapi import APIRouter

router = APIRouter()

@router.get("/analysis")
def get_stock_analysis():
    return {
        "status": "성공",
        "message": "주식 분석 API가 준비되었습니다. 나중에 여기에 yfinance와 Iceberg 분석 로직이 들어갑"
    }
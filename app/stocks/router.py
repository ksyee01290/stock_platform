"""
[주식 분석 도메인 - 엔드포인트 라우터]
- Frontend(React/Next.js)의 API 요청을 수신하는 문지기 역할을 합니다.
- [변경사항] 외부 API(yfinance) 호출 및 동시성 락(Lock) 을 제거하고, DB데이터를 즉시 투입
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta

from app.stocks import models, schemas
from app.database import get_db

router = APIRouter()

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
    

@router.get("/integrated/{ticker}", response_model=schemas.IntegratedStockResponse)
def get_stock_history(ticker: str, db: Session = Depends(get_db)):
    ticker = ticker.upper() # 대문자 변환 (aapl -> AAPL)
    
    # 검색 히스토리 로그 적재 (독립 트랜잭션 분리)
    try:
        search_log = models.SearchHistory(ticker=ticker)
        db.add(search_log)
        db.commit()
    except Exception as log_error:
        print(f"[Search Log Error] 검색 히스토리 적재 실패: {str(log_error)}")
        db.rollback()
        
    # DB 에서 마스터 주식 종목 조회
    existing_stock = db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
    
    if not existing_stock:
        raise HTTPException(
            status_code=status.HTTP_505_NOT_FOUND,
            detail=f"존재하지 않거나 플랫폼에 등록되지 않은 주식 입니다.: {ticker}"
        )
        
    # 1년 치 차트 데이터 선행 조회
    today = date.today()
    one_year_ago = today - timedelta(days=365)
    
    history_data = db.query(models.StockHistory)\
        .filter(models.StockHistory.ticker == ticker)\
        .filter(models.StockHistory.list_date >= one_year_ago)\
        .order_by(models.StockHistory.list_date.asc())\
        .all()
    
    safe_history = [schemas.StockHistoryResponse.model_validate(h) for h in history_data]
    
    score, risk, comment = calculate_stock_score(
        existing_stock.current_price,
        existing_stock.high_52week,
        existing_stock.low_52week
    )
    
    return {
        "status": "성공 (배치 최신 데이터)",
        "message": "백그라운드 수집 엔진에 의해 상시 동기화되는 안전한 데이터입니다.",
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

    
@router.get("/search/recent", response_model=list[schemas.RecentSearchResponse])
def get_recent_searches(db: Session = Depends(get_db)):
    """
    [최근 검색 종목 조회]
    - 최근 검색한 로그 30개를 긁어와 중복 없이 최신순 5개만 리턴
    """
    raw_logs = db.query(models.SearchHistory)\
        .order_by(models.SearchHistory.searched_at.desc())\
        .limit(30)\
        .all()
    seen = set()
    recent_searches = []
    for log in raw_logs:
        if log.ticker not in seen:
            seen.add(log.ticker)
            recent_searches.append(log)
        if len(recent_searches) == 5:
            break
        
    return recent_searches

@router.get("/search/trending", response_model=list[schemas.TrendingSearchResponse])
def get_trending_searches(db: Session = Depends(get_db)):
    """
    [실시간 인기 검색 순위 TOP 10]
    - 검색 히스토리 테이블 GROUP BY 하여 카운트된 상위 10개 종목
    """
    trending_data = db.query(
        models.SearchHistory.ticker,
        func.count(models.SearchHistory.ticker).label("search_count")
    )\
    .group_by(models.SearchHistory.ticker)\
    .order_by(func.count(models.SearchHistory.ticker).desc())\
    .limit(10)\
    .all()
    
    return [{"ticker": item.ticker, "search_count": item.search_count} for item in trending_data]

@router.post("/watchlist/{ticker}", response_model=schemas.WatchlistToggleResponse)
def toggle_watchlist(ticker: str, db: Session = Depends(get_db)):
    """ 
    [즐겨찾기 등록/해제 토글 API]
    -이미 즐겨찾기에 해당 주식이 있으면 -> 삭제 (is_favorite: False)
    -즐겨찾기에 해당 주식이 없으면 -> 추가 (is_favorite: True)
    """
    ticker = ticker.upper()
    
    stock_exists = db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
    if not stock_exists:
        raise HTTPException(status_code=404, detail=f"{ticker}는 아직 플랫폼에 등록되지 않았거나 존재하지 않는 주식입니다. 검색해 주세요")
    
    existing_favorite = db.query(models.Watchlist).filter(models.Watchlist.ticker == ticker).first()
    
    if existing_favorite:
        db.delete(existing_favorite)
        db.commit()
        return{
            "ticker": ticker,
            "is_favorite": False,
            "message": f"{ticker} 종목이 즐겨찾기에서 정상적으로 삭제되었습니다."
        }
    else:
        new_favorite = models.Watchlist(ticker=ticker)
        db.add(new_favorite)
        db.commit()
        return{
            "ticker": ticker,
            "is_favorite": True,
            "message": f"{ticker} 종목이 즐겨찾기에 추가되었습니다."
        }

@router.get("/watchlist", response_model=list[schemas.WatchlistItemResponse])
def get_watchlist(db: Session = Depends(get_db)):
    """
    [내 즐겨찾기 리스트 조회 API]
    -유저가 즐겨찾기한 동목들을 stocks 테이블과 조인
     현재가와 52주 최고/최저가 까지 모아서 보여줌
    """
    results = db.query(
        models.Watchlist.id,
        models.Stock.ticker,
        models.Stock.name,
        models.Stock.current_price,
        models.Stock.high_52week,
        models.Stock.low_52week
    ).join(models.Stock, models.Watchlist.ticker == models.Stock.ticker)\
     .order_by(models.Watchlist.created_at.desc())\
     .all()
     
    return [
         {
            "id": item.id,
            "ticker": item.ticker,
            "name": item.name,
            "current_price": item.current_price,
            "high_52week": item.high_52week,
            "low_52week": item.low_52week
         }
         for item in results
     ]
    
@router.get("/search/dashboard-init")
def get_dashboard_init(db: Session = Depends(get_db)):
    recent = get_recent_searches(db)
    trending = get_trending_searches(db)
    return {
        "recent": recent,
        "trending": trending
    }
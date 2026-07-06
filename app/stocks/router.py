"""
[주식 분석 도메인 - 엔드포인트 라우터]
- Frontend(React/Next.js)의 API 요청을 수신하는 문지기 역할을 합니다.
- [변경사항] 외부 API(yfinance) 호출 및 동시성 락(Lock) 을 제거하고, DB데이터를 즉시 투입
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta
import yfinance as yf

from app.auth.router import get_current_user
from app.stocks.models import User
from app.stocks import models, schemas
from app.stocks.services import (
    extract_live_price,
    extract_stock_name,
    build_history_from_dataframe,
)
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
        
    # DB 에서 마스터 주식 종목 조회
    existing_stock = db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
    
    #----------------------------------------
    # DB에 없는 완전한 새로운 종목을 유저가 검색하면 즉시 1년치 과거 데이터와 기본정보 수집
    #----------------------------------------
    if not existing_stock:
        print(f"{ticker}는 신규 종목입니다. 즉시 야후에서 수집을 시작합니다.")
        try:
            yf_ticker = yf.Ticker(ticker)
            stock_info = yf_ticker.info
            
            if not stock_info or ("regularMarketPrice" not in stock_info and "currentPrice" not in stock_info):
                raise HTTPException(status_code=404, detail=f"존재하지 않는 야후 파이낸스 입니다: {ticker}")
            live_price = extract_live_price(stock_info)
            
            existing_stock = models.Stock(
                ticker=ticker,
                name=extract_stock_name(stock_info, fallback=ticker),
                current_price=live_price,
                market_cap=stock_info.get("marketCap"),
                high_52week=stock_info.get("fiftyTwoWeekHigh"),
                low_52week=stock_info.get("fiftyTwoWeekLow"),
                updated_at=datetime.now()
            )
            db.add(existing_stock)
            db.commit()
            
            hist_df = yf_ticker.history(period="1y")
            history_items = build_history_from_dataframe(ticker, hist_df, fallback_price=live_price)
            if history_items:
                db.bulk_save_objects(history_items)
            
            db.commit()
            db.refresh(existing_stock)
            print(f"[On-Demand 수집 완료] {ticker} 종목 등록 및 1년 치 데이터 적재 성공!")
            
        except HTTPException as http_err:
            db.rollback()
            raise http_err
        except Exception as e:
            db.rollback()
            print(f"[On-Demand 에러 발생 인쇄] 구체적 에러 내용: {str(e)}")
            raise HTTPException(status_code=500,)
        
    try:
        search_log = models.SearchHistory(ticker=ticker)
        db.add(search_log)
        db.commit()
    except Exception as log_error:
        print(f"[Search Log Error] 검색 히스토리 적재 실패: {str(log_error)}")
        db.rollback()
        
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
def toggle_watchlist(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):
    """ 
    [즐겨찾기 등록/해제 토글 API]
    -이미 즐겨찾기에 해당 주식이 있으면 -> 삭제 (is_favorite: False)
    -즐겨찾기에 해당 주식이 없으면 -> 추가 (is_favorite: True)
    """
    ticker = ticker.upper()
    
    stock_exists = db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
    if not stock_exists:
        raise HTTPException(status_code=404, detail=f"{ticker}는 아직 플랫폼에 등록되지 않았거나 존재하지 않는 주식입니다. 검색해 주세요")
    
    existing_favorite = db.query(models.Watchlist).filter(
        models.Watchlist.ticker == ticker,
        models.Watchlist.user_id == current_user.id
        ).first()
    
    if existing_favorite:
        db.delete(existing_favorite)
        db.commit()
        return{
            "ticker": ticker,
            "is_favorite": False,
            "message": f"{ticker} 종목이 즐겨찾기에서 정상적으로 삭제되었습니다."
        }
    else:
        new_favorite = models.Watchlist(ticker=ticker, user_id=current_user.id)
        db.add(new_favorite)
        db.commit()
        return{
            "ticker": ticker,
            "is_favorite": True,
            "message": f"{ticker} 종목이 즐겨찾기에 추가되었습니다."
        }

@router.get("/watchlist", response_model=list[schemas.WatchlistItemResponse])
def get_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):
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
     .filter(models.Watchlist.user_id == current_user.id)\
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
    
@router.get("/portfolio/info")
def get_portfolio_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    [가상 자산 및 보유 주식 현황 조회 API]
    """
    holdings = db.query(
        models.Portfolio.id,
        models.Portfolio.ticker,
        models.Stock.name,
        models.Portfolio.quantity,
        models.Portfolio.average_price,
        models.Stock.current_price
    ).join(models.Stock, models.Portfolio.ticker == models.Stock.ticker)\
     .filter(models.Portfolio.user_id == current_user.id)\
     .all()
     
    portfolio_list = []
    for item in holdings:
        eval_value = item.current_price * item.quantity
        purchase_value = item.average_price * item.quantity
        profit_loss_rate = 0.0
        if purchase_value > 0:
            profit_loss_rate = ((eval_value - purchase_value) / purchase_value) * 100

        portfolio_list.append({
            "id": item.id,
            "ticker": item.ticker,
            "name": item.name,
            "quantity": item.quantity,
            "average_price": item.average_price,
            "current_price": item.current_price,
            "profit_loss_rate": round(profit_loss_rate, 2)
        })

    return {
        "cash_balance": current_user.cash_balance,
        "holdings": portfolio_list
    }
    
@router.post("/portfolio/buy")
def buy_stock(
    request: schemas.TradeRequest,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    [모의 가상자산 주식 매수 API]
    """
    ticker_upper = request.ticker.upper()
    
    stock = db.query(models.Stock).filter(models.Stock.ticker == ticker_upper).first()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"[{ticker_upper}]은 등록되지 않은 종목입니다. 먼저 검색하여 원본을 확보해 주세요."
        )
    
    total_cost = stock.current_price * request.quantity
    
    if current_user.cash_balance < total_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"가상 자산이 부족합니다. (필요: ${total_cost:,.2f} / 보유: ${current_user.cash_balance:,.2f})"
        )
        
    portfolio_item = db.query(models.Portfolio).filter(
        models.Portfolio.user_id == current_user.id,
        models.Portfolio.ticker == ticker_upper
    ).first()
    
    if portfolio_item:
        old_total_value = portfolio_item.quantity * portfolio_item.average_price
        new_total_value = total_cost
        new_quantity = portfolio_item.quantity + request.quantity
        
        portfolio_item.average_price = (old_total_value + new_total_value) / new_quantity
        portfolio_item.quantity = new_quantity
    else:
        new_portfolio = models.Portfolio(
            user_id=current_user.id,
            ticker=ticker_upper,
            quantity=request.quantity,
            average_price=stock.current_price
        )
        db.add(new_portfolio)
        
    current_user.cash_balance -= total_cost
    db.commit()
    
    return {
        "status": "success",
        "message": f"{stock.name}({ticker_upper}) {request.quantity}주 매수가 완료되었습니다!",
        "cash_balance": current_user.cash_balance
    }
    
@router.get("/search/suggest")
def get_stock_suggestions(q: str = "", db: Session = Depends(get_db)):
    """
    [주식 검색 자동완성 제안 API]
    - 사용자가 입력한 검색어(q)를 기준으로 종목코드 또는 회사명(name)에서
      유사한 종목을 최대 5개까지 찾아 반환합니다.
    """
    if not q or len(q.strip()) == 0:
        return []

    search_query = f"%{q.strip().upper()}%"
    
    suggestions = db.query(
        models.Stock.ticker,
        models.Stock.name,
        models.Stock.current_price
    ).filter(
        (models.Stock.ticker.like(search_query)) | 
        (func.upper(models.Stock.name).like(search_query))
    ).limit(5).all()
    
    result = []
    for item in suggestions:
        result.append({
            "ticker": item[0],         # models.Stock.ticker
            "name": item[1],           # models.Stock.name
            "current_price": item[2]   # models.Stock.current_price
        })
        
    return result
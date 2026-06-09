"""
[주식 분석 도메인 - 엔드포인트 라우터]
- Frontend(React/Next.js)의 API 요청을 수신하는 문지기 역할을 합니다.
- 3단계 하이브리드 데이터 관리 정책(DB 캐싱 + 5초 방어막 + 실시간 가격 패치)의 전체 흐름을 제어합니다.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta, timezone

import yfinance as yf
import threading

from app.stocks import models, schemas
from app.database import get_db

router = APIRouter()
stock_lock = threading.Lock()

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
    
    # [1단계] 검색 히스토리 로그 적재 (독립 트랜잭션 분리)
    try:
        search_log = models.SearchHistory(ticker=ticker)
        db.add(search_log)
        db.commit()
    except Exception as log_error:
        print(f"[Search Log Error] 검색 히스토리 적재 실패: {str(log_error)}")
        db.rollback()
    
    # [2단계] 1년 치 차트 데이터 선행 조회
    today = date.today()
    one_year_ago = today - timedelta(days=365)
    
    history_data = db.query(models.StockHistory)\
        .filter(models.StockHistory.ticker == ticker)\
        .filter(models.StockHistory.list_date >= one_year_ago)\
        .order_by(models.StockHistory.list_date.asc())\
        .all()   
    
    safe_history = [schemas.StockHistoryResponse.model_validate(h) for h in history_data]
    
    with stock_lock:
        db.rollback() # SQLAlchemy 세션 캐시 초기화 (최신 DB 스냅샷 확보)
        
        existing_stock = db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
        
        if existing_stock:    
            current_time = datetime.now()
            stock_updated_time = existing_stock.updated_at.replace(tzinfo=None) if existing_stock.updated_at.tzinfo else existing_stock.updated_at
            time_difference = current_time - stock_updated_time
            
            # 5초 방어막 정상화
            if 0 <= time_difference.total_seconds() < 5:
                print(f"[방어막 발동] {ticker} - {time_difference.total_seconds():.2f}초 만에 재요청 연타 감지.")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="과도한 연타가 감지되었습니다. 5초 후 다시 시도해주세요"
                )
                   
            # 1시간 이내 가격만 실시간 패치 구역
            if time_difference < timedelta(hours=1):
                print(f"[안정 구역] 1시간 이내 데이터 존재. 실시간 주가 검증 진행.")
                try:
                    # yf.Ticker(ticker) 인스턴스는 단발성이므로 그대로 한 줄 유지
                    live_info = yf.Ticker(ticker).info
                    live_price = live_info.get("currentPrice") or live_info.get("regularMarketPrice") or existing_stock.current_price
                    existing_stock.current_price = float(live_price)
                    existing_stock.updated_at = datetime.now()
                    db.commit()
                    db.refresh(existing_stock)
                except Exception as e:
                    print(f"[실시간 주가 패치 실패] {ticker} 실시간 가격 호출 실패, DB 값 활용: {str(e)}")
                    
                score, risk, comment = calculate_stock_score(existing_stock.current_price, existing_stock.high_52week, existing_stock.low_52week)
                
                return {
                    "status": "성공 (DB 최신 데이터)",
                    "message": f"1시간 이내에 업데이트된 데이터가 있습니다. (경과시간: {time_difference})",
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
        
        # [4단계] DB에 데이터가 없거나 1시간이 지난 경우 전체 라이브 데이터 수집 구역
        try:
            print(f"[라이브 호출] yfinance에서 {ticker} 신규/만료 데이터를 수집합니다.")
            
            yf_ticker = yf.Ticker(ticker)
            stock_info = yf_ticker.info
            
            # 없는 주식 예외 필터링 (404 예외 전환)
            if not stock_info or ("regularMarketPrice" not in stock_info and "currentPrice" not in stock_info):
                raise HTTPException(status_code=404, detail=f"존재하지 않거나 야후 파이낸스에서 찾을 수 없는 티커입니다: {ticker}")
            
            current_price = stock_info.get("currentPrice") or stock_info.get("regularMarketPrice") or 0.0
            
            target_stock = None
            status_msg = ""
            msg_detail = ""

            if existing_stock:
                existing_stock.name = stock_info.get("shortName") or stock_info.get("longName") or ticker
                existing_stock.current_price = float(current_price)
                existing_stock.market_cap = stock_info.get("marketCap")
                existing_stock.high_52week = stock_info.get("fiftyTwoWeekHigh")
                existing_stock.low_52week = stock_info.get("fiftyTwoWeekLow")
                existing_stock.updated_at = datetime.now()
                
                target_stock = existing_stock
                status_msg = "성공 (DB 업데이트 완료)"
                msg_detail = f"오래된 {ticker} 데이터를 새로 갱신했습니다."
            else:
                # 아예 없는 신규 종목 추가
                new_stock = models.Stock(
                    ticker=ticker,
                    name=stock_info.get("shortName") or stock_info.get("longName") or ticker,
                    current_price = float(current_price),
                    market_cap=stock_info.get("marketCap"),
                    high_52week=stock_info.get("fiftyTwoWeekHigh"),
                    low_52week=stock_info.get("fiftyTwoWeekLow"),
                    updated_at=datetime.now()
                )
                db.add(new_stock)
                
                target_stock = new_stock
                status_msg = "성공 (실시간 수집 + 차트 빌드)"
                msg_detail = f"yfinance에서 {ticker} 데이터를 실시간으로 가져와 DB에 저장했습니다."
                
                # =============================================================
                # 신규 종목일 때만 과거 1년 치 차트 데이터 수집 수행
                # =============================================================
                print(f"[자동 수집 발동!] {ticker} 종목의 과거 1년치 일일 주가 데이터를 수집합니다.")
                try:
                    hist_df = yf_ticker.history(period="1y")
                    
                    history_items = []
                    if hist_df is not None and not hist_df.empty:
                        for index, row in hist_df.iterrows():
                            list_date = index.date() if hasattr(index, 'date') else index
                            
                            open_p = row.get('Open') or row.get('open') or current_price
                            high_p = row.get('High') or row.get('high') or current_price
                            low_p = row.get('Low') or row.get('low') or current_price
                            close_p = row.get('Close') or row.get('close') or current_price
                            volume_v = row.get('Volume') or row.get('volume') or 0
                            
                            history_log = models.StockHistory(
                                ticker=ticker,
                                list_date=list_date,
                                open_price=float(open_p),
                                high_price=float(high_p),
                                low_price=float(low_p),
                                close_price=float(close_p),
                                volume=int(volume_v),
                                per=None,
                                pbr=None
                            )
                            history_items.append(history_log)
                        
                    if history_items:
                        db.bulk_save_objects(history_items)
                        print(f"[{ticker}] 총 {len(history_items)}건의 히스토리 데이터 적재 성공!")
                        safe_history = [schemas.StockHistoryResponse.model_validate(h) for h in history_items]
                    else:
                        safe_history = []
                
                except Exception as history_error:
                    print(f"[History 수집 경고] {ticker} 과거 주가 수집 실패 (기본 정보만 우선 저장): {str(history_error)}")
                    safe_history = [] # 예외 터져도 차트만 비우고 500 에러 차단

            db.commit()
            db.refresh(target_stock)

            score, risk, comment = calculate_stock_score(target_stock.current_price, target_stock.high_52week, target_stock.low_52week)
            
            return {
                "status": status_msg,
                "message": msg_detail,
                "data": {
                    "id": target_stock.id,
                    "ticker": ticker,
                    "name": target_stock.name,
                    "current_price": target_stock.current_price,
                    "market_cap": target_stock.market_cap,
                    "high_52week": target_stock.high_52week,
                    "low_52week": target_stock.low_52week          
                },
                "score": score,
                "risk_level": risk,
                "comment": comment,
                "history": safe_history
            }

        except HTTPException as http_err:
            db.rollback()
            raise http_err
        except Exception as e:
            db.rollback()
            if "404" in str(e) or "not found" in str(e).lower():
                raise HTTPException(status_code=404, detail=f"존재하지 않는 주식 티커입니다: {ticker}")
            raise HTTPException(status_code=500, detail=f"주식 데이터 수집 중 오류 발생: {str(e)}")
    
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
from pydantic import BaseModel
from datetime import date, datetime

class StockHistoryResponse(BaseModel):
    list_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    per: float | None
    pbr: float | None
    
    class Config:
        from_attributes = True
        
class IntegratedStockResponse(BaseModel):
    status: str
    message: str
    data: dict
    score: int
    risk_level: str
    comment: str
    history: list[StockHistoryResponse]
    
class RecentSearchResponse(BaseModel):
    """ 최근 검색어 응답 모델(시간 포함) """
    ticker: str
    searched_at: datetime
    
    class Config:
        from_attributes =True
        
class TrendingSearchResponse(BaseModel):
    """ 인기 검색어 응답 모델(카운트 포함) """
    ticker: str
    search_count: int
    
class WatchlistToggleResponse(BaseModel):
    """ 즐겨찾기 토글 결과 응답 모델"""
    ticker: str
    is_favorite: bool
    message: str
    
class WatchlistItemResponse(BaseModel):
    """ 즐겨찾기 목록 조회 응답 모델 """
    id: int
    ticker: str
    name: str
    current_price: float
    high_52week: float | None
    low_52week: float | None
    
# 유저 회원가입 및 인증 관련 스키마

class UserCreate(BaseModel):
    username: str
    password: str
    
class UserResponse(BaseModel):
    id: int
    username: str
    
    class Config:
        from_attributes = True
        
class Token(BaseModel):
    access_token: str
    token_type: str
    
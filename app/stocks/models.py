"""
[주식 분석 도메인 - 데이터베이스 모델 스키마]
- 기존의 '실시간 주가 테이블(Stock)' 구조를 유지합니다.
- 대용량 시계열(Time-Series) 과거 주가 기록 조회를 위해 'StockHistory' 테이블을 새롭게 설계했습니다.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime, ForeignKey, Date, Index
from sqlalchemy.sql import func 
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    """ 
    [유저 회원가입/로그인 테이블]
    - 유저의 고유 정보 및 패스워드(암호화 해시) 관리
    - 유저 삭제 시 즐겨찾기 및 검색 히스토리 자동 삭제
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # 모의투자용 예수금 추가
    cash_balance = Column(Float, default=10000000.0, nullable=False)
    
    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    search_histories = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    # 유저 탈퇴 시 자산 내역 삭제
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    
class Stock(Base):
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True) # 자동으로 1씩 증가하는 고유넘버
    ticker = Column(String, unique=True, index=True, nullable=False) # 주식 고유이름
    name = Column(String, nullable=False) # 종목명
    current_price = Column(Float, nullable=False) # 현재가
    market_cap = Column(BigInteger, nullable=True) # 시가총액
    high_52week = Column(Float, nullable=True) # 52주 최고가
    low_52week = Column(Float, nullable=True) # 52주 최저가
    
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
class StockHistory(Base):
    """
    - 종목별 과거 일일 주가 및 가치투자 지표 히스토리를 적재하는 거대한 데이터 창고
    """
    __tablename__ = "stock_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False, index=True)
    list_date = Column(Date, nullable=False, index=True)
    
    open_price = Column(Float, nullable=False)   # 시가
    high_price = Column(Float, nullable=False)   # 고가
    low_price = Column(Float, nullable=False)    # 저가
    close_price = Column(Float, nullable=False)  # 종가
    volume = Column(BigInteger, nullable=False)   # 거래량
    
    per = Column(Float, nullable=True) # 주가 수익비율
    pbr = Column(Float, nullable=True) # 주가 순자산율
    
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_ticker_list_date', 'ticker', 'list_date'),
    )
    
class Watchlist(Base):
    """
    [즐겨찾기 테이블 - 유저별 연동]
    - user_id 가 ticker 을 등록했는지 관계를 명시
    """
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String, ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="watchlists")
    
class SearchHistory(Base):
    """
    [검색 히스토리 테이블 - 유저별 연동]
    - 비로그인 유저 혹은 특정 유저가 검색한 기록을 나누어 적재
    """
    __tablename__ = "search_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    ticker = Column(String, ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False, index=True)
    searched_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="search_histories")
    
class Portfolio(Base):
    """
    [보유 주식 테이블 - 유저별 연동]
    - 유저가 몇주를 들고있는지 평단가 얼마에 들고있는지 기록
    """
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String, ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False, index=True)

    quantity = Column(Integer, default=0, nullable=False) # 보유 수량
    average_price = Column(Float, default=0.0, nulllable=False) # 매수 평단가
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", back_populates="portfolios")
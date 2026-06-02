"""
[주식 분석 도메인 - 데이터베이스 모델 스키마]
- 기존의 '실시간 주가 테이블(Stock)' 구조를 유지합니다.
- 대용량 시계열(Time-Series) 과거 주가 기록 조회를 위해 'StockHistory' 테이블을 새롭게 설계했습니다.
"""
from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime, ForeignKey, Date, Index
from sqlalchemy.sql import func 
from app.database import Base

class Stock(Base):
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True) # 자동으로 1씩 증가하는 고유넘버
    ticker = Column(String, unique=True, index=True, nullable=False) # 주식 고유이름
    name = Column(String, nullable=False) # 종목명
    current_price = Column(Float, nullable=False) # 현재가
    market_cap = Column(BigInteger, nullable=True) # 시가총액
    high_52week = Column(Float, nullable=True) # 52주 최고가
    low_52week = Column(Float, nullable=True) # 52주 최저가
    
    # 데이터가 처음들어올때와 수정될때 자동으로 현재시간 기록
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
class StockHistory(Base):
    """
    - 종목별 과거 일일 주가 및 가치투자 지표 히스토리를 적재하는 거대한 데이터 창고
    - 데이터가 1,000만 건 이상 쌓여도 초고속 조회가 가능하도록 복합 인덱스(Composite Index)를 적용
    """
    
    __tablename__ = "stock_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    # 외래 키 설정 : stocks 테이블의 ticker 삭제되면 연쇄 삭제(CASCADE)되도록 안정장치 구축
    ticker = Column(String, ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False, index=True)
    # 주가 기록 날짜 (시간 정보가 없는 날짜 전용 Date 타입)
    list_date = Column(Date, nullable=False, index=True)
    
    open_price = Column(Float, nullable=False)   # 시가
    high_price = Column(Float, nullable=False)   # 고가
    low_price = Column(Float, nullable=False)    # 저가
    close_price = Column(Float, nullable=False)  # 종가
    volume = Column(BigInteger, nullable=False)   # 거래량
    
    per = Column(Float, nullable=True) # 주가 수익비율
    pbr = Column(Float, nullable=True) # 주가 순자산율
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_ticker_list_date', 'ticker', 'list_date'),
    )
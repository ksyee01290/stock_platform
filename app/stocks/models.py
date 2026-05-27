from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime
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
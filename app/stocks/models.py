from sqlalchemy import Column, Integer, String, Float, BigInteger
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
    
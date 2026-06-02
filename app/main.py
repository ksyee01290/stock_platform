from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.stocks.router import router as stock_router

from app.database import engine, Base
from app.stocks import models

from contextlib import asynccontextmanager
from app.tasks.stock_tasks import start_scheduler, shutdown_scheduler

#  테이블구조 날려버리기
# Base.metadata.drop_all(bind=engine)

#  테이블구조 새로생성
Base.metadata.create_all(bind=engine)

# 스케줄러를 켜고 끄는 관리자 정의
@asynccontextmanager
async def lifespan(app: FastAPI):
    # [서버온] 백그라운드 스케줄러 가동
    start_scheduler()
    yield
    # [서버다운] 스케줄러도 메모리 누수 없이 종료
    shutdown_scheduler()

app = FastAPI(title= "주식 분석 플랫폼", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "성공", "message": "FastAPI 백엔드 서버가 정상적으로 켜졌습니다!"}

app.include_router(stock_router, prefix="/api/stocks", tags=["주식"])
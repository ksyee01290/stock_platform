from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.stocks.router import router as stock_router

app = FastAPI(title= "주식 분석 플랫폼")

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
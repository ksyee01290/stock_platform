# 📊 종합 데이터 분석 및 실시간 서비스 플랫폼 (stock_platform)

FastAPI 백엔드를 기반으로 한 실시간 주식 데이터 조회, 로또 번호 분석, 날씨 정보 제공 및 실시간 채팅을 통합한 풀스택 웹 애플리케이션입니다. 
순수 React 구조에서 시작하여 최종적으로 Next.js(App Router) 기반의 고성능 아키텍처로 확장하는 것을 목표로 합니다.

---

## 🚀 프로젝트 로드맵 (Roadmap)

본 프로젝트는 확장성과 유동성을 검증하기 위해 단계별 릴리즈를 목표로 합니다.
- **Phase 1 (진행 중):** FastAPI 백엔드 구축 및 `yfinance` 연동, PostgreSQL 데이터베이스 설계
- **Phase 2:** React를 이용한 컴포넌트 기반 프론트엔드 프로토타입 개발
- **Phase 3:** Next.js(App Router) 마이그레이션을 통한 파일 기반 라우팅 및 SSR(서버 사이드 렌더링) 도입
- **Phase 4:** WebSocket 기반의 실시간 채팅방 구현 및 서비스 고도화 (날씨, 로또 등)

---

## 🛠️ 기술 스택 (Tech Stack)

### Backend
- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL
- **Libraries:** uvicorn, yfinance

### Frontend (Planned)
- React.js ➡️ Next.js (App Router)

---

## 📂 폴더 구조 (Directory Structure)

도메인별로 완벽하게 격리되어 유동적인 확장이 가능한 백엔드 구조를 지향합니다.

```text
stock_platform/
├── app/                         # 백엔드 핵심 소스코드
│   ├── __init__.py
│   ├── main.py                  # 중앙 제어 및 라우터 등록
│   ├── stocks/                  # 주식 분석 도메인
│   │   ├── __init__.py
│   │   └── router.py
│   ├── lotto/                   # 로또 분석 도메인 (예정)
│   │   ├── __init__.py
│   │   └── router.py
│   └── weather/                 # 날씨 정보 도메인 (예정)
│       ├── __init__.py
│       └── router.py
├── frontend/                    # 프론트엔드 공간 (정적 파일 및 향후 프레임워크 전환)
└── venv/                        # 파이썬 가상환경
```

---

## ⚙️ 실행 방법 (How to Run)

### 1. 가상환경 활성화 및 패키지 설치
**Windows**
```Bash
.\venv\Scripts\activate
```
```text
패키지 설치 (yfinance, fastapi 등)
```

```Bash
pip install fastapi uvicorn yfinance
```
### 2. 백엔드 서버 실행
```Bash
uvicorn app.main:app --reload
기본 API 문서 주소: http://127.0.0.1:8000/docs
```
---

## 📌 주요 기능 (Key Features)

### 1. 주식 실시간 분석 (/api/stocks)
- yfinance 라이브러리를 연동하여 미국/한국 주식 시장의 실시간 데이터 수집

- 종목명, 현재가, 시가총액, 52주 최고가/최저가 추출 및 가공
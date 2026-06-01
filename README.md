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
- **Libraries:** uvicorn, yfinance, APScheduler(Background Task)

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
│   ├── database.py              # 데이터베이스
│   ├── tasks/                   # [배치 도메인] 백그라운드 자동화 작업 모음 공간
│   │   ├── __init__.py
│   │   ├── stock_tasks.py       # [배치 엔진] 주기적인 주식 지표 자동 갱신 및 DB 최신화
│   ├── stocks/                  # 주식 분석 도메인
│   │   ├── __init__.py
│   │   ├── models.py            # 주식데이터 종류
│   │   └── router.py            # [API 라우터] 주식 조회 및 하이브리드 로직 제어
│   ├── lotto/                   # 로또 분석 도메인 (예정)
│   │   ├── __init__.py
│   │   └── router.py            # [API 라우터] 로또 번호 분석 및 통계 API
│   └── weather/                 # 날씨 정보 도메인 (예정)
│       ├── __init__.py
│       └── router.py            # [API 라우터] 위치 기반 날씨 정보 연동 API
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

### 1. 주식 실시간 하이브리드 분석 및 트래픽 최적화 (/api/stocks)
- 3단계 하이브리드 데이터 관리: - [1단계 DB 조회]: 요청 시 먼저 DB에서 데이터를 조회합니다.

    - [2단계 유효시간 & 5초 캐싱 방어막]: 1시간 이내 데이터가 있다면 시총, 52주 최고/최저가 등 무거운 지표는 DB 값을 재활용하되, 현재 주가 딱 하나만 실시간 패치해 옵니다. 악의적인 연타 시 외부 API 차단을 막기 위해 5초 이내 중복 요청은 DB 데이터를 즉시 반환하는 방어막(Rate Limit)이 작동합니다.

    - [3단계 실시간 수집]: 데이터가 없거나 1시간이 지난 경우 전체 정보를 새로 긁어와 갱신합니다.

- 백그라운드 배치 시스템 (APScheduler): 서버가 구동되는 동안 백그라운드에서 주기적으로 DB 내 종목들을 자동 최신화하여 유저 검색 시 0.01초 만에 응답할 수 있도록 부하를 분산합니다.

### 2. 로또 번호 분석(/api/lotto - 예정)

- 역대 로또 당첨 번호 데이터를 기반으로 한 통계 및 분석 기능 제공

### 3. 날씨 정보 제공(/api/weather - 예정)

- 위치 기반 실시간 날씨 데이터 및 예보 정보 연동
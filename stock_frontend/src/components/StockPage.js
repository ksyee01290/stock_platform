import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import StockChart from '../StockChart';
import '../App.css';

function StockPage({ token, onRequireAuth }) {
    const [ticker, setTicker] = useState('');
    const [suggestions, setSuggestions] = useState([]);
    const [stockData, setStockData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // 모의투자용 상태값
    const [cashBalance, setCashBalance] = useState(10000000);
    const [buyQuantity, setBuyQuantity] = useState(1);
    const [myHoldings, setMyHoldings] = useState([]);

    // 최근 검색어 및 인기검색어 및 즐겨찾기
    const [recentSearches, setRecentSearches] = useState([]);
    const [trendingSearches, setTrendingSearches] = useState([]);
    const [watchlist, setWatchlist] = useState([]);

    // 백엔드 사이드바 통계 데이터
    const fetchSidebarAndWatchlist = useCallback(async () =>{
        try{
            const dashboardRes = await axios.get('http://127.0.0.1:8000/api/stocks/search/dashboard-init');
            const { recent, trending } = dashboardRes.data;
            if (recent && Array.isArray(recent)) setRecentSearches(recent);
            if (trending && Array.isArray(trending)) setTrendingSearches(trending);

            if (token) {
                const authHeader = { headers: { Authorization: `Bearer ${token}` } };
                const watchlistRes = await axios.get('http://127.0.0.1:8000/api/stocks/watchlist', authHeader);
                setWatchlist(watchlistRes.data);
            } else {
                setWatchlist([]);
            }
        } catch (err) {
            console.error('통계 데이터를 가져오는데 실패했습니다.', err);
        }
    }, [token]);

    useEffect(()=>{
        fetchSidebarAndWatchlist();
    }, [fetchSidebarAndWatchlist]);

    const fetchPortfolioInfo = useCallback(async () => {
        if (!token) return; // 로그인이 안 되어 있으면 중단
        try {
            const authHeader = { headers: { Authorization: `Bearer ${token}` } };
            const res = await axios.get('http://127.0.0.1:8000/api/stocks/portfolio/info', authHeader);
            
            // 백엔드의 실제 잔액으로 갱신합니다!
            setCashBalance(res.data.cash_balance);
            setMyHoldings(res.data.holdings || []);
        } catch (err) {
            console.error('가상 자산 정보를 가져오는데 실패했습니다.', err);
        }
    }, [token]);

    // 페이지가 처음 켜지거나, 로그인 상태(token)가 바뀔 때 자금 상태를 불러옴
    useEffect(() => {
        if (token) {
            fetchPortfolioInfo();
        }
    }, [token, fetchPortfolioInfo]);

    const handleSearch = async () => {
        if (!ticker) return alert('종목을 입력해주세요 (예: AAPL)');
        await executeSearch(ticker);
    };

    const handleInputChange = async (e) => {
        const val = e.target.value;
        setTicker(val);

        if (!val || val.trim() === '') {
            setSuggestions([]);
            return;
        }

        try {
            const res = await axios.get(`http://127.0.0.1:8000/api/stocks/search/suggest?q=${val}`);
            setSuggestions(res.data || []);
        } catch (err) {
            console.error('검색 추천 목록 조회 실패:', err);
        }
    };

    // 최근 검색어나 인기 순위를 클릭했을때도 동작할 공통 검색 로직
    const executeSearch = async(targetTicker) =>{
        if (!targetTicker) return;
        setLoading(true);
        
        try {
            const cleanTicker = targetTicker.trim();
            const response = await axios.get(`http://127.0.0.1:8000/api/stocks/integrated/${cleanTicker}`);
            setError(null);
            setStockData(response.data);
            fetchSidebarAndWatchlist();
        } catch (err) {
            console.error(err);

            if (err.response && err.response.status === 429){
                const backendMessage = err.response.data.detail || '과도한 요청입니다. 잠시 후 시도하세요.';
                alert(backendMessage);
            } else{
                setStockData(null);
                setError('주식 데이터를 가져오는데 실패했습니다.');
            }
        } finally {
            setLoading(false);
        }
    };

    // 즐겨찾기 등록/해제 토글버튼 함수
    const handleToggleWatchlist = async (targetTicker) => {
        if (!token) {
            alert('즐겨찾기 기능은 로그인이 필요합니다.');
            onRequireAuth();
            return;
        }

        try {
            const authHeader = { headers: { Authorization: `Bearer ${token}` } };
            const response = await axios.post(`http://127.0.0.1:8000/api/stocks/watchlist/${targetTicker.trim()}`, {}, authHeader);
            alert(response.data.message);
            fetchSidebarAndWatchlist(); // 좌측 리스트 갱신
        } catch (err) {
            alert(err.response?.data?.detail || '즐겨찾기 토글 실패');
        }
    };

    // 주식 매수 주문을 요청하는 함수
    const handleBuyStock = async () => {
        if (!token) {
            alert('모의투자는 로그인이 필요한 기능입니다.');
            if (typeof onRequireAuth === 'function') onRequireAuth();
            return;
        }

        if (!info || !info.ticker) {
            alert('종목을 먼저 검색해 주세요.');
            return;
        }

        try {
            const authHeader = { headers: { Authorization: `Bearer ${token}` } };
            const payload = {
                ticker: info.ticker,
                quantity: parseInt(buyQuantity, 10)
            };

            const response = await axios.post('http://127.0.0.1:8000/api/stocks/portfolio/buy', payload, authHeader);
            
            alert(response.data.message);
            fetchPortfolioInfo();
            setBuyQuantity(1);
        } catch (err) {
            console.error('매수 주문 실패:', err.response?.data);
            alert(err.response?.data?.detail || '매수 주문에 실패했습니다.');
        }
    };

    const info = stockData?.data ? stockData.data : stockData;
    const isCurrentFavorite = watchlist.some(item => item.ticker === info?.ticker);

    const calculateTotalProfitLoss = () => {
        if (!myHoldings || myHoldings.length === 0) return 0;

        return myHoldings.reduce((sum, item) => {
            const currentVal = (item.current_price || 0) * item.quantity;
            const purchaseVal = (item.average_price || 0) * item.quantity;
            return sum + (currentVal - purchaseVal);
        }, 0);
    };
    const totalProfitLossAmount = calculateTotalProfitLoss();

    // 52주 최고/최저가 대비 현재 가격 위치 백분율 계산 로직
    const calculatePosition = () => {
        if(!info || !info.current_price || !info.high_52week || !info.low_52week) return 0;
        const high = parseFloat(info.high_52week);
        const low = parseFloat(info.low_52week);
        const current = parseFloat(info.current_price);
        if (high === low) return 0;
        const percentage = ((current - low) / (high - low)) * 100;
        return Math.min(Math.max(percentage,0), 100);
    };
    const currentPositionPercent = calculatePosition();

    return(
        <div className="page-box stock-theme">
            <h3> 주식 분석 구역</h3>
            <div className="search-bar-zone">
                <input
                    type="text"
                    value={ticker}
                    placeholder="종목 입력 (예: AAPL)"
                    className="search-input"
                    onChange={handleInputChange}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                            handleSearch();
                            setSuggestions([]);
                        }
                    }}
                />
                <button onClick={handleSearch} className="search-button" disabled={loading}>
                    {loading ? '조회 중...' : '조회'}
                </button>

                {/*실시간 자동완성 추천 결과가 있을 때만 활성화*/}
                {suggestions.length > 0 && (
                    <div className="search-suggest-dropdown">
                        {suggestions.map((item) => (
                            <div
                                key={item.ticker}
                                onClick={() => {
                                    setTicker(item.ticker);
                                    setTimeout(() => {
                                        handleSearch();
                                    }, 0);
                                    setSuggestions([]);
                                }}
                                className="search-suggest-item"
                            >
                                <div>
                                    <span className="rank-ticker" style={{ fontWeight: 'bold' }}>{item.ticker}</span>
                                    <span className="search-suggest-name">{item.name}</span>
                                </div>
                                <span className="search-suggest-price">
                                    ${item.current_price?.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {error && <p className="error-text-message"> 에러: {error}</p>}
            {loading && <div className="chart-loading">통합 서버 창고에서 정밀 데이터 패치 중...</div>}

            <div className="stock-main-layout">
                {/* 좌측영역 */}
                <div className="stock-left-content">
                    {stockData && info ? (
                        <div className="dashboard-left-stack">
                            {/* 1. 상단 주식 상세 정보 카드 */}
                            <div className="result-card">
                                <div className="stock-title-area">
                                    <h4>{info.name || ticker} ({info.ticker || ticker})</h4>
                                    <button onClick={() => handleToggleWatchlist(info.ticker || ticker)} className="favorite-toggle-btn">
                                        {isCurrentFavorite ? '⭐' : '☆'}
                                    </button>
                                </div>

                                <div className="stock-info-grid">
                                    <p><strong>현재 가격:</strong> ${info.current_price || 'N/A'}</p>
                                    <p><strong>시가 총액:</strong> ${info.market_cap ? info.market_cap.toLocaleString() : 'N/A'}</p>
                                    <p><strong>52주 최고가:</strong> ${info.high_52week || 'N/A'}</p>
                                    <p><strong>52주 최저가:</strong> ${info.low_52week || 'N/A'}</p>
                                </div>

                                {/* 52주 주가 위치 비주얼 게이지 바 영역 */}
                                <div className="price-range-bar-container">
                                    <div className="price-range-label">
                                        <span>52주 최저 (${info.low_52week})</span>
                                        <span>52주 최고 (${info.high_52week})</span>
                                    </div>
                                    <div className="price-range-track">
                                        {/* 대쉬보드 내 인라인 완전 배제를 위해 스타일 속성 대신 custom property로 변수만 전달 */}
                                        <div 
                                            className="price-range-pointer" 
                                            style={{ '--current-pos': `${currentPositionPercent}%` }}
                                        />
                                    </div>
                                </div>
                                
                                {/* 2. 자체 위험도 분석 리포트 */}
                                <div className="analysis-report-box">
                                    <h5 className="analysis-title">자체 위험도 분석 리포트</h5>
                                    
                                    <p className="analysis-text-line">
                                        <strong>주가 위치 점수:</strong> {stockData.score}점 / 100점
                                    </p>
                                    
                                    <p className="analysis-text-line">
                                        <strong>위험도 등급:</strong> {' '}
                                        <span className={
                                            stockData.score <= 30 ? 'risk-safe' : stockData.score <= 70 ? 'risk-normal' : 'risk-danger'
                                        }>
                                            {stockData.risk_level || '분석 중'}
                                        </span>
                                    </p>
                                    
                                    <p className="analysis-comment-card">
                                        {stockData.comment || '데이터 분석 완료'}
                                    </p>
                                </div>
                                
                                <p className="system-status-text">
                                    시스템 상태: {stockData.message || '정상'}
                                </p>
                            </div>

                            {/* 3. 하단 독립형 차트 대시보드 레이어 */}
                            <div className="chart-card-container">
                                <div className="chart-header">
                                    <h4 className="chart-title">{info.ticker || ticker} 기술적 분석 차트</h4>
                                    <span className="chart-subtitle">정밀 시계열 히스토리</span>
                                </div>
                                <div className="chart-wrapper">
                                    <StockChart 
                                        ticker={info.ticker || ticker} 
                                        historyData={stockData.history} 
                                    />
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="result-card empty-dashboard-state">
                            분석할 주식을 검색해 주세요.
                        </div>
                    )}
                </div>

                {/* 우측영역 */}
                <div className="stock-right-sidebar">
                    {/* 내 관심 종목 구역 */}
                    <div className="dashboard-stat-box watchlist-box">
                        <h5 className="dashboard-stat-title">⭐ 내 관심 종목</h5>
                        <div className="watchlist-list">
                            {watchlist.length === 0 ? (
                                <p className="dashboard-no-data">즐겨찾기한 주식이 없습니다.</p>
                            ) : (
                                watchlist.map((item) => (
                                    <div key={item.id} onClick={() => { setTicker(item.ticker); executeSearch(item.ticker); }} className="trending-rank-item watchlist-item-clickable">
                                        <span className="rank-ticker">{item.ticker}</span>
                                        <span className="watchlist-price">${item.current_price}</span>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                    {token &&(
                        <>
                            {/* 모의투자*/}
                            <div className="dashboard-stat-box mock-investment-box">
                                <h5 className="dashboard-stat-title"> 가상 모의투자 (MVP)</h5>
                                
                                <div className="mock-investment-info">
                                    <p><strong>보유 자산:</strong> ${cashBalance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
                                    <p><strong>예상 결제액:</strong> ${( (info?.current_price || 0) * buyQuantity ).toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
                                </div>

                                <div className="mock-investment-action">
                                    <input 
                                        type="number" 
                                        min="1" 
                                        value={buyQuantity} 
                                        onChange={(e) => setBuyQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                                        className="mock-quantity-input"
                                    />
                                    <button className="mock-buy-button" onClick={handleBuyStock}>
                                        매수하기
                                    </button>
                                </div>
                            </div>

                            <div className="dashboard-stat-box">
                                <div className="mock-portfolio-header">
                                    <h5 className="dashboard-stat-title mock-portfolio-title">내 투자 현황</h5>
                                    <span className={`mock-total-profit-loss ${
                                        totalProfitLossAmount > 0 ? 'profit' : totalProfitLossAmount < 0 ? 'loss' : ''
                                        }`}>
                                        {totalProfitLossAmount > 0 
                                            ? `+$${totalProfitLossAmount.toLocaleString(undefined, { maximumFractionDigits: 2 })}` 
                                            : `$${totalProfitLossAmount.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
                                        }
                                    </span>
                                </div>
                                <div className="watchlist-list">
                                    {myHoldings.length === 0 ? (
                                        <p className="dashboard-no-data">보유 중인 주식이 없습니다.</p>
                                    ) : (
                                        myHoldings.map((item) => (
                                            <div 
                                                key={item.id} 
                                                onClick={() => { setTicker(item.ticker); executeSearch(item.ticker); }} 
                                                className="trending-rank-item watchlist-item-clickable"
                                            >
                                                <div>
                                                    <span className="rank-ticker">{item.ticker}</span>
                                                    <span style={{ fontSize: '12px', color: '#64748b', marginLeft: '6px' }}>{item.quantity}주</span>
                                                </div>
                                                {/* 수익률 양수/음수에 따라 색상 조절 */}
                                                <span style={{ 
                                                    fontSize: '13px', 
                                                    fontWeight: 'bold', 
                                                    color: item.profit_loss_rate > 0 ? '#ef4444' : item.profit_loss_rate < 0 ? '#3b82f6' : '#64748b' 
                                                }}>
                                                    {item.profit_loss_rate > 0 ? `+${item.profit_loss_rate}` : item.profit_loss_rate}%
                                                </span>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </>
                    )}

                    {/* 최근 검색한 종목 */}
                    <div className="dashboard-stat-box">
                        <h5 className="dashboard-stat-title"> 최근 검색 종목</h5>
                        <div>
                            {recentSearches.length === 0 ? (
                                <p className="dashboard-no-data">검색 기록이 없습니다.</p>
                            ) : (
                                recentSearches.map((item,idx) => (
                                    <span
                                        key={idx}
                                        onClick={() => {
                                            setTicker(item.ticker);
                                            setTimeout(() => { handleSearch(); }, 0);
                                        }}
                                        className="recent-ticker-badge"
                                    >
                                        {item.ticker}
                                    </span>
                                ))
                            )}
                        </div>
                    </div>
                    
                    {/* 실시간 인기 순위 */}
                    <div className="dashboard-stat-box">
                        <h5 className="dashboard-stat-title">실시간 인기 순위</h5>
                        <ul className="trending-rank-list">
                            {trendingSearches.length === 0 ? (
                                <p className="dashboard-no-data">순위 데이터가 없습니다.</p>
                            ) : (
                                trendingSearches.map((item, index) => (
                                    <li
                                        key={index}
                                        onClick={() => {
                                            setTicker(item.ticker);
                                            executeSearch(item.ticker);
                                        }}
                                        className="trending-rank-item"
                                    >
                                        <div>
                                            <span className="rank-number">{index + 1}</span>
                                            <span className="rank-ticker">{item.ticker}</span>
                                        </div>
                                        <span className="rank-count">{item.search_count}회</span>
                                    </li>
                                ))
                            )}
                        </ul>
                    </div>

                </div>{/* 우측 영억 끝 */}

            </div>{/* 메인 레이아웃 끝 */}
        </div>
    );
}

export default StockPage;
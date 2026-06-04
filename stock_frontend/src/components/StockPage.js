import React, { useState, useEffect } from 'react';
import axios from 'axios';
import StockChart from '../StockChart';
import '../App.css';

function StockPage({ renderChart }) {
    const [ticker, setTicker] = useState('');
    const [stockData, setStockData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // 최근 검색어 및 인기검색어
    const [recentSearches, setRecentSearches] = useState([]);
    const [trendingSearches, setTrendingSearches] = useState([]);

    // 백엔드 사이드바 통계 데이터
    const fetchSidebarData = async () =>{
        try{
            const response = await axios.get('http://127.0.0.1:8000/api/stocks/search/dashboard-init');
            
            console.log("통합 대시보드 원본데이터:", response.data);

            const { recent, trending } = response.data;
            if (recent && Array.isArray(recent)) setRecentSearches(recent);
            if (trending && Array.isArray(trending)) setTrendingSearches(trending);
        } catch (err) {
            console.error('통계 데이터를 가져오는데 실패했습니다.', err);
        }
    };

    useEffect(()=>{
        fetchSidebarData();
    }, []);

    // 기존 유지 및 수정
    const handleSearch = async () => {
        if (!ticker) return alert('종목을 입력해주세요 (예: AAPL)');
        await executeSearch(ticker);
    };

    // 최근 검색어나 인기 순위를 클릭했을때도 동작할 공통 검색 로직
    const executeSearch = async(targetTicker) =>{
        if (!targetTicker) return;
        setLoading(true);
        setError(null);
        setStockData(null);
        
        try {
            const cleanTicker = targetTicker.toUpperCase();
            const response = await axios.get(`http://127.0.0.1:8000/api/stocks/integrated/${cleanTicker}`);
            setStockData(response.data);

            fetchSidebarData();
        } catch (err) {
            console.error(err);
            setError('주식 데이터를 가져오는데 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const info = stockData?.data ? stockData.data : stockData;

    return(
        <div className="page-box stock-theme">
            <h3> 주식 분석 구역</h3>
            <div>
                <input
                    type="text"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    placeholder="종목 입력 (예: AAPL)"
                    className="search-input"
                />
                <button onClick={handleSearch} className="search-button" disabled={loading}>
                    {loading ? '조회 중...' : '조회'}
                </button>
            </div>

            {error && <p style={{ color: 'red'}}> 에러: {error}</p>}
            {loading && <div className="chart-loading">통합 서버 창고에서 정밀 데이터 패치 중...</div>}

            <div className="stock-main-layout">
                {/* 좌측영역 */}
                <div className="stock-left-content">
                    {stockData && info ? (
                        <div className="result-card" style={{ marginTop: 0}}>
                            <h4> {info.name || ticker} ({info.ticker || ticker})</h4>
                            <p><strong>현재 가격:</strong> ${info.current_price || 'N/A'}</p>
                            <p><strong>시가 총액:</strong> ${info.market_cap ? info.market_cap.toLocaleString() : 'N/A'}</p>
                            <p><strong>52주 최고가:</strong> ${info.high_52week || 'N/A'}</p>
                            <p><strong>52주 최저가:</strong> ${info.low_52week || 'N/A'}</p>
                            
                            <hr />
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
                            
                            <hr />
                            <p style={{ fontSize: '12px', color: '#666' }}>
                                시스템 상태: {stockData.message || '정상'}
                            </p>
                            <div style={{ marginTop: '30px' }}>
                                <StockChart 
                                    ticker={info.ticker || ticker} 
                                    historyData={stockData.history} 
                                />
                        </div>
                    </div>
                    ) : (
                        <div className="result-card" style={{ marginTop: 0, padding: '40px', textAlign: 'center', color: '#a0aec0' }}>
                            분석할 주식을 검색해 주세요.
                        </div>
                    )}
                </div>

                {/* 우측영역 */}
                <div className="stock-right-sidebar">
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
                                            executeSearch(item.ticker);
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
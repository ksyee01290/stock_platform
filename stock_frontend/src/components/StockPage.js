import React, { useState } from 'react';
import axios from 'axios';
import StockChart from '../StockChart';
import '../App.css';

function StockPage({ renderChart }) {
    const [ticker, setTicker] = useState('');
    const [stockData, setStockData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSearch = async () => {
        if (!ticker) return alert('종목을 입력해주세요 (예: AAPL)');

        setLoading(true);
        setError(null);
        setStockData(null);
        

        try {
            const response = await axios.get(`http://127.0.0.1:8000/api/stocks/integrated/${ticker}`);
            setStockData(response.data);
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

            {stockData && info && (
                <div className="result-card">
                    <h4> {info.name || ticker} ({info.ticker || ticker})</h4>
                    <p><strong>현재 가격:</strong> ${info.current_price || 'N/A'}</p>
                    <p><strong>시가 총액:</strong> ${info.market_cap ? info.market_cap.toLocaleString() : 'N/A'}</p>
                    <p><strong>52주 최고가:</strong> ${info.high_52week || 'N/A'}</p>
                    <p><strong>52주 최저가:</strong> ${info.low_52week || 'N/A'}</p>
                    
                    <hr />
                    <div className="analysis-report-box">
                        <h5 className="analysis-title">🧠 자체 위험도 분석 리포트</h5>
                        
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
            )}
        </div>
    );
}

export default StockPage;
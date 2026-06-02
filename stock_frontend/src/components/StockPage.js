import React, { useState } from 'react';
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

        try{
            const response = await fetch(`http://127.0.0.1:8000/api/stocks/analysis/${ticker}`);
            if (!response.ok) {
                throw new Error('주식 데이터를 가져오는데 실패했습니다.');
            }
            const result = await response.json();
            setStockData(result);
        } catch  (err){
            setError(err.message);
        } finally{
            setLoading(false);
        }
    };

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
                <button onClick={handleSearch} className="search-button">
                    {loading ? '조회 중...' : '조회'}
                </button>
            </div>

            {error && <p style={{ color: 'red'}}> 에러: {error}</p>}

            {stockData && (
                <div className="result-card">
                    <h4> {stockData.data.name} ({stockData.data.ticker})</h4>
                    <p><strong>현재 가격:</strong> ${stockData.data.current_price}</p>
                    <p><strong>시가 총액:</strong> ${stockData.data.market_cap?.toLocaleString()}</p>
                    <p><strong>52주 최고가:</strong> ${stockData.data.high_52week}</p>
                    <p><strong>52주 최저가:</strong> ${stockData.data.low_52week}</p>
                    
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
                            {stockData.risk_level}
                        </span>
                        </p>
                        
                        <p className="analysis-comment-card">
                        📢 {stockData.comment}
                        </p>
                    </div>
                    
                    <hr />
                    <p style={{ fontSize: '12px', color: '#666' }}>
                        시스템 상태: {stockData.message}
                    </p>
                    {renderChart && renderChart(stockData.data.ticker)}
                </div>
            )}
        </div>
    );
}

export default StockPage;
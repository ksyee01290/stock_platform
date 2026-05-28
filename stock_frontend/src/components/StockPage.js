import React, { useState } from 'react';

function StockPage() {
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
        <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#fafafa'}}>
            <h3> 주식 분석 구역</h3>
            <div style={{ marginBottom: '20px' }}>
                <input
                    type="text"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    placeholder="종목 입력 (예: AAPL)"
                    style={{ padding: '8px', marginRight: '10px', textTransform: 'uppercase'}}
                />
                <button onClick={handleSearch} style={{ padding: '8px 15px', cursor: 'pointer'}}>
                    {loading ? '조회 중...' : '조회'}
                </button>
            </div>

            {error && <p style={{ color: 'red'}}> 에러: {error}</p>}

            {stockData && (
                <div style={{ border: '1px solid #ccc', padding: '15px', borderRadius: '5px', backgroundColor: '#fff'}}>
                    <h4> {stockData.data.name} ({stockData.data.ticker})</h4>
                    <p><strong>현재 가격:</strong> ${stockData.data.current_price}</p>
                    <p><strong>시가 총액:</strong> ${stockData.data.market_cap?.toLocaleString()}</p>
                    <p><strong>52주 최고가:</strong> ${stockData.data.high_52week}</p>
                    <p><strong>52주 최저가:</strong> ${stockData.data.low_52week}</p>
                    <hr />
                    <p style={{ fontSize: '12px', color: '#666' }}>
                        시스템 상태: {stockData.message}
                    </p>
                </div>
            )}
        </div>
    );
}

export default StockPage;
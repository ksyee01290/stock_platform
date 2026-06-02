import React, { useState } from 'react';
import StockPage from './components/StockPage';
import StockChart from './StockChart';
import './App.css';

function App() {
  const [currentTab, setCurrentTab] = useState('stock');

  return (
    <div className="container">
      <h1>멀티 분석 플랫폼</h1>

      <div className="tab-bar">
        <button
          onClick={() => setCurrentTab('stock')}
          className={`tab-button ${currentTab === 'stock' ? 'active' : ''}`}
        >
          주식 분석
        </button>
        <button
          onClick={() => setCurrentTab('weather')}
          className={`tab-button ${currentTab === 'weather' ? 'active' : ''}`}
        >
          날씨 예보 (준비중)
        </button>
        <button
          onClick={() => setCurrentTab('lotto')}
          className={`tab-button ${currentTab === 'lotto' ? 'active' : ''}`}
        >
          로또 예측 (준비중)
        </button>
      </div>

      <hr style={{ border: '0', height: '1px', backgroundColor: '#e2e8f0', margin: '20px 0' }} />

      <div className="content-container">
        
        {/* 주식 분석 탭 활성화 시 */}
        {currentTab === 'stock' && (
          <div>
            <StockPage renderChart={(tickerValue) => (
              <div style={{ marginTop: '30px' }}>
                <StockChart ticker={tickerValue} />
              </div>
            )} />
          </div>
        )}

        {/* 날씨 예보 탭 활성화 시 */}
        {currentTab === 'weather' && (
          <div className="page-box weather-theme">
            <h3>날씨 예보 구역</h3>
            <p>데이터 유효기간 관리 알고리즘 반영 예정 구역입니다.</p>
          </div>
        )}

        {/* 로또 예측 탭 활성화 시 */}
        {currentTab === 'lotto' && (
          <div className="page-box lotto-theme">
            <h3>로또 예측 구역</h3>
            <p>로또 번호 분석 및 통계 알고리즘 반영 예정 구역입니다.</p>
          </div>
        )}
        
      </div>
    </div>
  );
}

export default App;
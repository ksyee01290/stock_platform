import React, { useState } from 'react';
import StockPage from './components/StockPage';

function App() {

  const [currentTab, setCurrentTab] = useState('stock');

  return(
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto', fontFamily: 'sans-serif' }}>
      <h1>멀티 분석 플랫폼</h1>

      {/* 탭 메뉴 영역: 유동적확장을 위한 상단바 미리만듬*/}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px'}}>
        <button
          onClick={() => setCurrentTab('stock')}
          style={{ padding: '10px 20px', cursor: 'pointer', backgroundColor: currentTab === 'stock' ? '#bbb' : '#eee'}}
        >
          주식 분석
        </button>
        <button 
          onClick={() => setCurrentTab('weather')}
          style={{ padding: '10px 20px', cursor: 'pointer', backgroundColor: currentTab === 'weather' ? '#bbb' : '#eee' }}
        >
          날씨 예보 (준비중)
        </button>
        <button 
          onClick={() => setCurrentTab('lotto')}
          style={{ padding: '10px 20px', cursor: 'pointer', backgroundColor: currentTab === 'lotto' ? '#bbb' : '#eee' }}
        >
          로또 예측 (준비중)
        </button>
      </div>
      
      <hr />

      {/* 조건부 렌더링: 선택된 탬에 맞는 화면 부품만 유동적으로 갈아끼움 */}
      <div style={{ marginTop: '20px' }}>
        {currentTab === 'stock' && <StockPage />}

        {currentTab === 'weather' && (
          <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#e8f5e9' }}>
            <h3>☀️ 날씨 예보 구역</h3>
            <p>데이터 유효기간 관리 알고리즘 반영 예정 구역입니다.</p>
          </div>
        )}
        
        {currentTab === 'lotto' && (
          <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#fff3e0' }}>
            <h3>🎰 로또 예측 구역</h3>
            <p>로또 번호 분석 및 통계 알고리즘 반영 예정 구역입니다.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
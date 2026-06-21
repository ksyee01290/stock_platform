import React, { useState } from 'react';
import StockPage from './components/StockPage';
import axios from 'axios';
import './App.css';

function App() {
  const [currentTab, setCurrentTab] = useState('stock');
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [showAuthPage, setShowAuthPage] = useState(false);
  const [isSignUp, setIsSignUp] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post('http://127.0.0.1:8000/api/auth/login', { 
        username: username, 
        password: password 
      });
      
      const accessToken = response.data.access_token;
      localStorage.setItem('token', accessToken);
      setToken(accessToken);
      setShowAuthPage(false);
      alert('로그인에 성공했습니다!');
    } catch (err){
      console.error("로그인 에러 상세:", err.response?.data);
      alert(err.response?.data?.detail || '로그인 실패. 아이디나 비밀번호를 확인하세요.');
    }
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    try {
      await axios.post('http://127.0.0.1:8000/api/auth/signup', { 
        username: username, 
        password: password 
      });

      alert('회원가입이 완료되었습니다! 로그인해 주세요.');
      setIsSignUp(false);
    } catch (err) {
      console.error("회원가입 에러 상세:", err.response?.data);
      alert(err.response?.data?.detail || '회원가입 실패. 이미 존재하는 아이디 입니다.');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken('');
    window.location.reload();
  };

  if (showAuthPage) {
    return (
      <div className="container auth-container">
        <h1>멀티 분석 플랫폼</h1>
        <div className="page-box auth-theme">
          <h3>{isSignUp ? '회원가입' : '로그인'}</h3>
          <form onSubmit={isSignUp ? handleSignUp : handleLogin}>
            <input
              type="text"
              placeholder="아이디"
              className="search-input auth-input-full"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="비밀번호"
              className="search-input auth-input-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button type="submit" className="search-button auth-submit-button">
              {isSignUp ? '가입하기' : '로그인'}
            </button>
          </form>
          <button onClick={() => setIsSignUp(!isSignUp)} className="tab-button auth-toggle-button">
            {isSignUp ? '이미 계정이 있으신가요? 로그인' : '계정이 없으신가요? 회원가입'}
          </button>
          <button onClick={() => setShowAuthPage(false)} className="tab-button auth-toggle-button" style={{ marginTop: '5px', color: '#a0aec0' }}>
            뒤로가기 (비회원으로 이용)
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`container ${currentTab === 'stock' ? 'wide-layout' : ''}`}>
      <div className="app-header-zone">
        <h1>멀티 분석 플랫폼</h1>
        {token ? (
          <button onClick={handleLogout} className="search-button logout-button">
            로그아웃
          </button>
        ) : (
          <button onClick={() => setShowAuthPage(true)} className="search-button">
            로그인 / 회원가입
          </button>
        )}
      </div>

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

      <hr className="tab-divider" />

      <div className="content-container">
        
        {/* 주식 분석 탭 활성화 시 */}
        {currentTab === 'stock' && (
          <div>
            <StockPage token={token} onRequireAuth={() => setShowAuthPage(true)} />
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
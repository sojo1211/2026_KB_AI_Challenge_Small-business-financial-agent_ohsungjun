import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([
    {
      sender: 'agent',
      text: `안녕하세요! 2026 KB 국민은행 AI Challenge '소상공인 금융 지원 AI Agent'입니다.\n\n소상공인을 위한 정책자금 및 금융상품 정보, 상권 및 경기 지표 트렌드, 그리고 비대면 가맹점 심사를 위한 고객확인(KYC/AML) 법령 가이드라인까지 신속하게 안내해 드립니다.\n\n궁금한 내용을 직접 입력하시거나 좌측의 추천 질문을 클릭해 보세요!`,
      sources: []
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const messageEndRef = useRef(null);

  // 자동 스크롤
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // 추천 질문 카테고리 정의
  const recommendedCategories = [
    {
      name: "💸 정책자금 및 금융상품",
      questions: [
        "소상공인 정책자금 신청 자격과 제한 대상은 무엇인가요?",
        "신용보증기금의 보증상품 성과평가 결과를 요약해 주실래요?"
      ]
    },
    {
      name: "📊 상권 및 경영 데이터",
      questions: [
        "소상공인시장진흥공단의 상권정보 데이터 포맷은 어떻게 구성되어 있나요?"
      ]
    },
    {
      name: "📈 경기 및 소비 데이터",
      questions: [
        "전라남도 소비자물가지수 추이에 대해 설명해 주실래요?"
      ]
    },
    {
      name: "🛡️ KYC/AML 금융 규제 데이터",
      questions: [
        "비대면 가맹점 심사 시 고객확인제도(KYC) 필수 확인 항목은 무엇인가요?",
        "전자금융업 감독규정상 자금세탁방지(AML) 내부통제 절차는 어떻게 되나요?"
      ]
    }
  ];

  // 메시지 전송 핸들러
  const handleSendMessage = async (textToSend) => {
    const queryText = textToSend || input;
    if (!queryText.trim()) return;

    // 사용자 메시지 추가
    const userMessage = { sender: 'user', text: queryText, sources: [] };
    setMessages((prev) => [...prev, userMessage]);
    
    if (!textToSend) {
      setInput(''); // 직접 입력한 경우 입력창 초기화
    }

    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: queryText }),
      });

      if (!response.ok) {
        throw new Error('서버 응답 에러');
      }

      const data = await response.json();
      
      const agentMessage = {
        sender: 'agent',
        text: data.generation,
        sources: data.sources || []
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (error) {
      console.error('API Error:', error);
      const errorMessage = {
        sender: 'agent',
        text: '❌ 에이전트와 통신하는 과정에서 오류가 발생했습니다. FastAPI 서버가 정상적으로 켜져 있는지 확인해 주세요 (Port: 8000).',
        sources: []
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // 엔터 키 핸들러
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !isLoading) {
      handleSendMessage();
    }
  };

  return (
    <div className="app-container">
      {/* 1. 상단 최상위 경진대회 배너 */}
      <div className="kb-banner">
        <span className="kb-banner-badge">현직자 Pick 주제</span>
        <span>2026 KB 국민은행 제8회 AI Challenge 경진대회</span>
        <img 
          src="/star-friends.png" 
          className="star-friends-img" 
          alt="KB 스타프렌즈 스토리" 
        />
      </div>

      {/* 3. 메인 분할 화면 */}
      <div className="main-layout">
        
        {/* 좌측 사이드바: 과거 대화 기록 */}
        <aside className="sidebar">
          <div className="sidebar-section">
            <div className="sidebar-title">
              <span>💬</span> 대화 기록
            </div>

            <div className="history-date-group">
              <div className="history-date-label">오늘</div>
              <div className="history-item active">
                <span className="history-icon">💸</span>
                <div className="history-item-content">
                  <div className="history-item-header">
                    <span className="history-item-title">소상공인 정책자금 자격요건</span>
                    <span className="history-item-time">10:24</span>
                  </div>
                  <div className="history-item-preview">신청 자격과 제한 대상 안내</div>
                </div>
              </div>
              <div className="history-item">
                <span className="history-icon">🛡️</span>
                <div className="history-item-content">
                  <div className="history-item-header">
                    <span className="history-item-title">KYC 필수 확인 항목 정리</span>
                    <span className="history-item-time">10:15</span>
                  </div>
                  <div className="history-item-preview">비대면 가맹점 심사 기준</div>
                </div>
              </div>
              <div className="history-item">
                <span className="history-icon">📊</span>
                <div className="history-item-content">
                  <div className="history-item-header">
                    <span className="history-item-title">상권정보 데이터 포맷 분석</span>
                    <span className="history-item-time">09:42</span>
                  </div>
                  <div className="history-item-preview">소상공인시장진흥공단 API</div>
                </div>
              </div>
              <div className="history-item">
                <span className="history-icon">📈</span>
                <div className="history-item-content">
                  <div className="history-item-header">
                    <span className="history-item-title">전라남도 소비자물가 추이</span>
                    <span className="history-item-time">09:11</span>
                  </div>
                  <div className="history-item-preview">2024~2025 물가지수 트렌드</div>
                </div>
              </div>
              <div className="history-item">
                <span className="history-icon">🏦</span>
                <div className="history-item-content">
                  <div className="history-item-header">
                    <span className="history-item-title">신용보증기금 보증상품 평가</span>
                    <span className="history-item-time">08:30</span>
                  </div>
                  <div className="history-item-preview">성과평가 결과 요약</div>
                </div>
              </div>
              <div className="history-item">
                <span className="history-icon">⚖️</span>
                <div className="history-item-content">
                  <div className="history-item-header">
                    <span className="history-item-title">AML 내부통제 절차 가이드</span>
                    <span className="history-item-time">08:05</span>
                  </div>
                  <div className="history-item-preview">전자금융업 감독규정 안내</div>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* 우측 챗 스크린 */}
        <main className="chat-area">
          <div className="agent-info-bar">
            <div className="agent-info-left">
              <div className="agent-avatar">🤖</div>
              <div className="agent-name-box">
                <div className="agent-name">금융 지원 AI 에이전트</div>
                <div className="agent-status">실시간 작동 중</div>
              </div>
            </div>
          </div>

          <div className="message-list">
            {messages.map((msg, index) => (
              <div key={index} className={`message-wrapper ${msg.sender}`}>
                <div className={`message-avatar ${msg.sender}`}>
                  {msg.sender === 'agent' ? '🤖' : '👤'}
                </div>
                <div className="message-content-box">
                  <div className="sender-name">
                    {msg.sender === 'agent' ? 'AI Agent' : '사용자'}
                  </div>
                  <div className="message-bubble">
                    {msg.text}
                    
                    {/* 출처 표시 (에이전트 메시지이고 출처가 있을 때) */}
                    {msg.sender === 'agent' && msg.sources && msg.sources.length > 0 && (
                      <div className="sources-container">
                        <div className="sources-title">📌 참고 출처</div>
                        <div className="sources-list">
                          {msg.sources.map((src, srcIdx) => (
                            <span key={srcIdx} className="source-badge">
                              {src}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {/* 로딩 표시 */}
            {isLoading && (
              <div className="message-wrapper agent">
                <div className="message-avatar">🤖</div>
                <div className="message-content-box">
                  <div className="sender-name">AI Agent</div>
                  <div className="message-bubble loading-bubble">
                    <div className="dot"></div>
                    <div className="dot"></div>
                    <div className="dot"></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messageEndRef} />
          </div>

          {/* 추천 질문 카테고리 (가로 배치) */}
          <div className="recommendation-bar">
            {recommendedCategories.map((category, idx) => (
              <div key={idx} className="recommendation-category-wrapper">
                <div className="recommendation-category">{category.name}</div>
                <div className="recommendation-tooltip">
                  {category.questions.map((question, qIdx) => (
                    <button
                      key={qIdx}
                      className="recommendation-tooltip-item"
                      onClick={() => handleSendMessage(question)}
                      disabled={isLoading}
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* 하단 입력바 */}
          <div className="chat-input-bar">
            <input
              type="text"
              className="chat-input"
              placeholder="AI 에이전트에게 소상공인 금융 규제 및 정책자금에 대해 질문해 보세요..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            <button
              className="send-button"
              onClick={() => handleSendMessage()}
              disabled={isLoading || !input.trim()}
            >
              전송
            </button>
          </div>
        </main>
      </div>

      {/* 하단 개발자 정보 */}
      <footer className="app-footer">
        <span>소상공인 금융 지원을 위한 오성준 개발자 입니다.</span>
      </footer>
    </div>
  );
}

export default App;

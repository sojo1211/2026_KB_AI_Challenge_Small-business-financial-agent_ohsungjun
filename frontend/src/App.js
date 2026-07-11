import React, { useState, useRef, useEffect } from 'react';
import './App.css';

const WELCOME_MESSAGE = {
  sender: 'agent',
  text: `안녕하세요! 2026 KB 국민은행 AI Challenge '소상공인 금융 지원 AI Agent'입니다.\n\n소상공인을 위한 정책자금 및 금융상품 정보, 상권 및 경기 지표 트렌드, 그리고 비대면 가맹점 심사를 위한 고객확인(KYC/AML) 법령 가이드라인까지 신속하게 안내해 드립니다.\n\n궁금한 내용을 직접 입력하시거나 좌측의 추천 질문을 클릭해 보세요!`,
  sources: []
};

// 초기 Mock 대화 기록 (포트폴리오 시연용)
const initialConversations = [
  {
    id: 'conv-1',
    title: '소상공인 정책자금 자격요건',
    preview: '신청 자격과 제한 대상 안내',
    icon: '💸',
    time: '10:24',
    messages: [
      { ...WELCOME_MESSAGE },
      { sender: 'user', text: '소상공인 정책자금 신청 자격과 제한 대상은 무엇인가요?', sources: [] },
      { sender: 'agent', text: '소상공인 정책자금은 「소상공인 보호 및 지원에 관한 법률」에 따라 상시근로자 5인 미만(제조·건설·운수업 등은 10인 미만) 사업체를 대상으로 합니다.\n\n✅ 신청 자격:\n• 사업자등록증 보유 소상공인\n• 업력 제한 없음 (신규 창업자도 가능)\n• 신용등급 무관 (단, 연체 이력에 따라 한도 차등)\n\n❌ 제한 대상:\n• 유흥·도박·사행성 업종\n• 임대업 (부동산 임대)\n• 금융·보험업\n• 세금 체납자 (국세·지방세)\n\n자금 종류별로 세부 조건이 다르니, 소상공인진흥공단(1357)이나 소상공인마당 홈페이지에서 세부 요건을 확인하시길 권장합니다.', sources: ['소상공인 보호 및 지원에 관한 법률', '소상공인진흥공단 정책자금 안내'] }
    ]
  },
  {
    id: 'conv-2',
    title: 'KYC 필수 확인 항목 정리',
    preview: '비대면 가맹점 심사 기준',
    icon: '🛡️',
    time: '10:15',
    messages: [
      { ...WELCOME_MESSAGE },
      { sender: 'user', text: '비대면 가맹점 심사 시 고객확인제도(KYC) 필수 확인 항목은 무엇인가요?', sources: [] },
      { sender: 'agent', text: '비대면 가맹점 심사 시 고객확인제도(KYC)에서 필수적으로 확인해야 하는 항목은 다음과 같습니다.\n\n📋 필수 확인 항목:\n1. **신원확인**: 대표자 성명, 생년월일, 실명번호\n2. **사업자 진위확인**: 사업자등록번호 진위 여부 (국세청 API 연동)\n3. **실제 소유자 확인**: 법인의 경우 최종 실소유자(25% 이상 지분 보유자)\n4. **거래 목적 확인**: 가맹점 계약의 목적 및 자금 출처\n5. **위험 평가**: 업종별 자금세탁 위험도 등급 분류\n\n⚠️ 강화된 확인(EDD) 대상:\n• 고위험 업종 (귀금속, 환전, 가상자산 등)\n• PEP(정치적 주요인물) 관련 사업체\n• 해외 거래가 빈번한 가맹점', sources: ['고객확인제도(CDD) 가이드라인', '전자금융감독규정'] }
    ]
  },
  {
    id: 'conv-3',
    title: '상권정보 데이터 포맷 분석',
    preview: '소상공인시장진흥공단 API',
    icon: '📊',
    time: '09:42',
    messages: [
      { ...WELCOME_MESSAGE },
      { sender: 'user', text: '소상공인시장진흥공단의 상권정보 데이터 포맷은 어떻게 구성되어 있나요?', sources: [] },
      { sender: 'agent', text: '소상공인시장진흥공단의 상권정보 API는 다양한 상권 분석 데이터를 제공합니다.\n\n📁 주요 데이터 카테고리:\n1. **상권영역 정보**: 상권코드, 상권명, 경계좌표(GeoJSON)\n2. **점포 데이터**: 업종대분류/중분류/소분류, 점포수, 개폐업 추이\n3. **매출 데이터**: 시간대별·요일별·연령대별 카드 매출액\n4. **유동인구**: 시간대별 유동인구 수, 성별/연령별 비율\n5. **임대료 정보**: 구역별 평균 임대료, 공실률\n\n🔗 API 호출 형식:\n• REST API (JSON 응답)\n• 인증키 필요 (공공데이터포털에서 발급)\n• 일 1,000건 호출 제한 (무료 등급)', sources: ['소상공인시장진흥공단 OpenAPI 명세서'] }
    ]
  },
  {
    id: 'conv-4',
    title: '전라남도 소비자물가 추이',
    preview: '2024~2025 물가지수 트렌드',
    icon: '📈',
    time: '09:11',
    messages: [
      { ...WELCOME_MESSAGE },
      { sender: 'user', text: '전라남도 소비자물가지수 추이에 대해 설명해 주실래요?', sources: [] },
      { sender: 'agent', text: '전라남도 소비자물가지수(CPI, 2020=100)의 최근 추이를 요약하면 다음과 같습니다.\n\n📊 연간 추이:\n• 2023년: 111.76 (전년비 +3.5%)\n• 2024년: 114.25 (전년비 +2.2%)\n• 2025년: 116.78 (전년비 +2.2%)\n\n📈 2026년 월별 동향:\n• 1월: 118.41 (+2.3%)\n• 3월: 119.43 (+2.7%)\n• 5월: 120.38 (+3.6%) ← 상승 가속\n\n💡 분석 포인트:\n물가상승률이 2025년 초 2.0% 수준에서 2026년 5월 3.6%로 가속 상승 중입니다. 특히 신선식품지수의 변동성이 높아, 소상공인 식자재 비용 부담이 증가하는 추세입니다.', sources: ['한국은행 ECOS (https://ecos.bok.or.kr)', '통계청 소비동향조사'] }
    ]
  },
  {
    id: 'conv-5',
    title: '신용보증기금 보증상품 평가',
    preview: '성과평가 결과 요약',
    icon: '🏦',
    time: '08:30',
    messages: [
      { ...WELCOME_MESSAGE },
      { sender: 'user', text: '신용보증기금의 보증상품 성과평가 결과를 요약해 주실래요?', sources: [] },
      { sender: 'agent', text: '신용보증기금의 주요 보증상품 성과평가 결과를 요약 드립니다.\n\n🏦 주요 보증상품 현황:\n• 일반보증: 소상공인·중소기업 대상, 보증비율 85~100%\n• 유동화보증: 매출채권 담보 유동화 지원\n• 창업보증: 사업개시 7년 이내 기업 대상\n\n📊 성과 요약 (2025년 기준):\n• 보증잔액: 약 72.5조원\n• 보증기업 수: 약 28만개사\n• 사고율: 3.2% (전년 대비 0.3%p 개선)\n• 보증기업 매출 증가율: 평균 8.4%\n\n✅ 핵심 평가:\n보증 지원을 받은 소상공인의 생존율이 미지원 기업 대비 약 15%p 높으며, 특히 창업 초기 3년 내 생존율 향상에 기여하고 있습니다.', sources: ['신용보증기금 연차보고서', '중소기업 금융지원 성과평가'] }
    ]
  },
  {
    id: 'conv-6',
    title: 'AML 내부통제 절차 가이드',
    preview: '전자금융업 감독규정 안내',
    icon: '⚖️',
    time: '08:05',
    messages: [
      { ...WELCOME_MESSAGE },
      { sender: 'user', text: '전자금융업 감독규정상 자금세탁방지(AML) 내부통제 절차는 어떻게 되나요?', sources: [] },
      { sender: 'agent', text: '전자금융업 감독규정에 따른 자금세탁방지(AML) 내부통제 절차는 다음과 같이 구성됩니다.\n\n📝 필수 내부통제 절차:\n1. **보고책임자(CO) 지정**: AML 전담 보고책임자 선임 의무\n2. **고객확인(CDD)**: 신규 고객 등록 시 신원확인 및 위험평가\n3. **거래 모니터링**: 이상거래 탐지 시스템(FDS) 운영\n4. **의심거래보고(STR)**: 의심되는 거래 발견 시 금융정보분석원(FIU)에 보고\n5. **고액현금거래보고(CTR)**: 1회 2,000만원 이상 현금거래 자동 보고\n\n⚠️ 위반 시 제재:\n• 과태료: 최대 1억원\n• 영업정지: 최대 6개월\n• 임직원 제재: 해임권고, 직무정지 등\n\n📌 전자금융업자는 연 1회 이상 AML 교육을 실시하고, 내부감사를 통해 절차 이행 여부를 점검해야 합니다.', sources: ['전자금융감독규정 (금융위원회고시)', '자금세탁방지 유권해석 사례집 2.0'] }
    ]
  }
];

function App() {
  const [conversations, setConversations] = useState(initialConversations);
  const [activeConvId, setActiveConvId] = useState('conv-1');
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const messageEndRef = useRef(null);

  // 현재 활성 대화 가져오기
  const activeConversation = conversations.find(c => c.id === activeConvId);
  const messages = activeConversation ? activeConversation.messages : [];

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

  // 대화 전환 핸들러
  const handleSelectConversation = (convId) => {
    setActiveConvId(convId);
  };

  // 새 대화 시작 핸들러
  const handleNewChat = () => {
    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
    const newConv = {
      id: `conv-${Date.now()}`,
      title: '새 대화',
      preview: '새로운 질문을 입력해 보세요',
      icon: '✨',
      time: timeStr,
      messages: [{ ...WELCOME_MESSAGE }]
    };
    setConversations(prev => [newConv, ...prev]);
    setActiveConvId(newConv.id);
  };

  // 메시지 전송 핸들러
  const handleSendMessage = async (textToSend) => {
    const queryText = textToSend || input;
    if (!queryText.trim()) return;

    const userMessage = { sender: 'user', text: queryText, sources: [] };
    
    // 현재 대화에 사용자 메시지 추가 + 제목/미리보기 업데이트
    setConversations(prev => prev.map(conv => {
      if (conv.id === activeConvId) {
        const isFirstUserMsg = !conv.messages.some(m => m.sender === 'user');
        return {
          ...conv,
          title: isFirstUserMsg ? queryText.substring(0, 20) + (queryText.length > 20 ? '...' : '') : conv.title,
          preview: queryText.substring(0, 30),
          messages: [...conv.messages, userMessage]
        };
      }
      return conv;
    }));
    
    if (!textToSend) {
      setInput('');
    }

    setIsLoading(true);

    try {
      const API_URL = 'https://kb-ai-agent-backend.onrender.com';
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: queryText }),
      });

      if (!response.ok) throw new Error('서버 응답 에러');

      const data = await response.json();
      
      const agentMessage = {
        sender: 'agent',
        text: data.generation,
        sources: data.sources || []
      };

      setConversations(prev => prev.map(conv => {
        if (conv.id === activeConvId) {
          return { ...conv, messages: [...conv.messages, agentMessage] };
        }
        return conv;
      }));
    } catch (error) {
      console.error('API Error:', error);
      const errorMessage = {
        sender: 'agent',
        text: '❌ 에이전트와 통신하는 과정에서 오류가 발생했습니다. FastAPI 서버가 정상적으로 켜져 있는지 확인해 주세요 (Port: 8000).',
        sources: []
      };
      setConversations(prev => prev.map(conv => {
        if (conv.id === activeConvId) {
          return { ...conv, messages: [...conv.messages, errorMessage] };
        }
        return conv;
      }));
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
              <button className="new-chat-btn" onClick={handleNewChat}>
                + 새 대화
              </button>
            </div>

            <div className="history-date-group">
              <div className="history-date-label">오늘</div>
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`history-item ${conv.id === activeConvId ? 'active' : ''}`}
                  onClick={() => handleSelectConversation(conv.id)}
                >
                  <span className="history-icon">{conv.icon}</span>
                  <div className="history-item-content">
                    <div className="history-item-header">
                      <span className="history-item-title">{conv.title}</span>
                      <span className="history-item-time">{conv.time}</span>
                    </div>
                    <div className="history-item-preview">{conv.preview}</div>
                  </div>
                </div>
              ))}
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

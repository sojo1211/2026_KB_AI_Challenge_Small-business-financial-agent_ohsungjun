import os
import re
from typing import List, Dict, Any
from typing_extensions import TypedDict

# LangChain & LangGraph
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END
from duckduckgo_search import DDGS

# ==========================================
# 0. 출처 포맷팅 헬퍼 함수
# ==========================================
def clean_source_label(source_path: str) -> str:
    path_normalized = source_path.replace("\\", "/")
    
    if "1-1.중소벤처기업부" in path_normalized:
        return "중소벤처기업부 (https://www.mss.go.kr)"
    elif "1-2.소상공인시장진흥공단" in path_normalized:
        return "소상공인시장진흥공단 (https://www.semas.or.kr)"
    elif "1-3.신용보증기금" in path_normalized:
        return "신용보증기금 (https://www.kodit.co.kr)"
    elif "1-4.기술보증기금" in path_normalized:
        return "기술보증기금 (https://www.kibo.or.kr)"
    elif "1-5.KB국민은행" in path_normalized:
        return "KB국민은행 (https://obank.kbstar.com)"
    elif "2-1.소상공인" in path_normalized or "상권정보" in path_normalized:
        return "소상공인시장진흥공단 상권정보 (https://sg.sbiz.or.kr)"
    elif "2-2" in path_normalized or "공공데이터" in path_normalized:
        return "공공데이터포털 (https://www.data.go.kr)"
    elif "2-3.KOSIS" in path_normalized or "통계청" in path_normalized:
        return "KOSIS 국가통계포털 (https://kosis.kr)"
    elif "3-1.한국은행 ECOS" in path_normalized:
        return "한국은행 ECOS (https://ecos.bok.or.kr)"
    elif "4-1.분석(FIU)" in path_normalized or "고객확인" in path_normalized:
        return "금융정보분석원(FIU) (https://www.kofiu.go.kr)"
    elif "4-2.안내" in path_normalized or "자금세탁방지" in path_normalized:
        return "금융위원회 (https://www.fsc.go.kr)"
    elif "4-3.지침" in path_normalized:
        return "금융감독원 (https://www.fss.or.kr)"
    
    return os.path.basename(source_path)

# ==========================================
# 1. State 정의
# ==========================================
class AgentState(TypedDict):
    question: str          # 사용자 질문
    documents: List[Document]  # 검색/수집된 문서 조각들
    web_search: bool       # 웹 검색 수행 여부
    generation: str        # 최종 답변
    sources: List[str]     # 출처 목록

# ==========================================
# 2. 전역 설정 및 초기화
# ==========================================
def load_api_key():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        return api_key
        
    env_path = "./.env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if "=" in line:
                    parts = line.split("=", 1)
                    key = parts[0].strip()
                    val = parts[1].strip().strip("'").strip('"')
                    if key in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
                        return val
                elif line.startswith("AQ"):
                    return line
    return None

api_key = load_api_key()
if not api_key:
    raise ValueError("❌ .env 파일에서 Gemini API 키를 찾을 수 없습니다. API 키를 등록해 주세요.")

os.environ["GEMINI_API_KEY"] = api_key
os.environ["GOOGLE_API_KEY"] = api_key

# 2.1 임베딩 모델 및 리트리버 로드
print("🧠 임베딩 모델(multilingual-e5-small) 로드 중...")
embeddings = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-small",
    model_kwargs={'device': 'cuda'},  # GPU 가속
    encode_kwargs={'normalize_embeddings': True}
)

db_dir = "./chroma_db"
if not os.path.exists(db_dir):
    raise FileNotFoundError(f"❌ Vector DB가 존재하지 않습니다: {db_dir}. 2번 스크립트를 먼저 실행하세요.")

print("💾 Chroma Vector DB 로드 중...")
vectorstore = Chroma(
    persist_directory=db_dir,
    embedding_function=embeddings
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

# 2.2 LLM 모델 로드
print("🤖 Gemini 2.5 Flash 모델 초기화 중...")
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2, max_retries=0)

# ==========================================
# 3. 도구(Tools) 정의
# ==========================================
def web_search_tool(query: str) -> str:
    """필요한 정보가 벡터 DB에 없을 경우 DuckDuckGo를 통해 웹 검색 수행"""
    print(f"🌐 [웹 검색 실시] '{query}' 검색 중...")
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            if results:
                formatted = []
                for r in results:
                    formatted.append(f"[출처: {r['href']}]\n내용: {r['body']}")
                return "\n\n".join(formatted)
    except Exception as e:
        print(f"⚠️ 웹 검색 중 에러 발생: {e}")
    return ""

# ==========================================
# 4. LangGraph 노드(Nodes) 정의
# ==========================================
def retrieve_node(state: AgentState) -> Dict[str, Any]:
    question = state["question"]
    documents = retriever.invoke(question)
    return {"documents": documents, "question": question}

def grade_documents_node(state: AgentState) -> Dict[str, Any]:
    question = state["question"]
    documents = state["documents"]
    
    if not documents:
        return {"documents": [], "question": question, "web_search": True}

    grader_prompt = (
        "당신은 검색된 문서 조각이 사용자의 질문과 관련이 있는지 평가하는 평가관입니다.\n"
        "제공된 문서가 사용자 질문에 답변하기에 유용하고 유의미한 내용을 포함하고 있다면 'yes'를,\n"
        "전혀 관련이 없거나 쓸모없는 정보라면 'no'라고 답하세요. 다른 부가 설명 없이 오직 'yes' 또는 'no'만 출력하세요.\n\n"
        "사용자 질문: {question}\n"
        "검색된 문서:\n{document}\n\n"
        "답변:"
    )

    filtered_docs = []
    web_search = False

    for doc in documents:
        try:
            prompt = grader_prompt.format(question=question, document=doc.page_content)
            res = llm.invoke(prompt)
            grade = res.content.strip().lower()
            if "yes" in grade:
                filtered_docs.append(doc)
        except Exception as e:
            print(f"⚠️ [Document Grader] LLM 호출 실패 (Fallback 적용): {e}")
            filtered_docs.append(doc)

    if not filtered_docs:
        web_search = True

    return {"documents": filtered_docs, "question": question, "web_search": web_search}

def web_search_node(state: AgentState) -> Dict[str, Any]:
    question = state["question"]
    documents = state["documents"]
    
    search_results = web_search_tool(question)
    if search_results:
        search_doc = Document(
            page_content=search_results,
            metadata={"source": "실시간 웹 검색 (DuckDuckGo)"}
        )
        documents.append(search_doc)
        
    return {"documents": documents, "question": question}

def generate_node(state: AgentState) -> Dict[str, Any]:
    question = state["question"]
    documents = state["documents"]
    
    context_parts = []
    sources = []
    seen_sources = set()
    
    for doc in documents:
        raw_src = doc.metadata.get('source', '알 수 없음')
        src = clean_source_label(raw_src)
        page = doc.metadata.get('page', 0) + 1
        
        source_label = f"{src} (Page {page})" if "page" in doc.metadata else src
        if source_label not in seen_sources:
            sources.append(source_label)
            seen_sources.add(source_label)
            
        context_parts.append(f"[출처: {source_label}]\n{doc.page_content}")
        
    context = "\n\n".join(context_parts)

    # 지침서 파일(guideline.md) 로드
    guideline_path = "./guideline.md"
    if os.path.exists(guideline_path):
        with open(guideline_path, "r", encoding="utf-8") as f:
            guideline_content = f.read()
    else:
        guideline_content = "당신은 소상공인 금융 지원 AI 에이전트입니다."

    system_prompt = f"{guideline_content}\n\nContext:\n{{context}}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    chain = prompt | llm
    
    try:
        res = chain.invoke({"context": context, "input": question})
        generation = res.content
    except Exception as e:
        print(f"⚠️ [Generate Node] LLM 호출 실패 (Fallback 적용): {e}")
        # API 오류가 나더라도 RAG가 검색해 온 원본 문서를 가공하여 사용자에게 돌려줍니다.
        if documents:
            doc_contents = []
            for doc in documents[:2]:
                raw_src = doc.metadata.get('source', '알 수 없음')
                src = clean_source_label(raw_src)
                doc_contents.append(f"📄 [출처: {src}]\n{doc.page_content}")
            
            joined_docs = "\n\n".join(doc_contents)
            generation = (
                "⚠️ 현재 API 호출 횟수 제한(무료 등급)으로 인해 AI가 답변을 깔끔하게 요약하지 못했습니다.\n"
                "대신 DB에서 검색된 가장 관련성 높은 원본 문서 내용을 공유해 드립니다:\n\n"
                f"{joined_docs}"
            )
        else:
            generation = (
                "⚠️ 현재 API 호출 횟수 제한으로 인해 답변을 생성할 수 없으며,\n"
                "데이터베이스에서도 관련된 내용을 찾지 못했습니다."
            )

    return {"generation": generation, "documents": documents, "sources": sources}

# ==========================================
# 5. LangGraph 흐름(Graph) 설계 및 빌드
# ==========================================
workflow = StateGraph(AgentState)

# 5.1 노드 등록
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade_documents", grade_documents_node)
workflow.add_node("web_search", web_search_node)
workflow.add_node("generate", generate_node)

# 5.2 엣지 연결
workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "grade_documents")

# 웹 검색 수행 여부에 따른 분기(Conditional Edge) 정의
def decide_to_generate(state: AgentState) -> str:
    if state["web_search"]:
        return "web_search"
    else:
        return "generate"

workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {
        "web_search": "web_search",
        "generate": "generate"
    }
)
workflow.add_edge("web_search", "generate")
workflow.add_edge("generate", END)

# 5.3 그래프 컴파일
app = workflow.compile()

# ==========================================
# 6. 메인 실행 인터페이스
# ==========================================
def main():
    print("\n" + "="*80)
    print("🤖 LangGraph 기반 '소상공인 금융 지원 AI Agent' 구동 완료!")
    print("="*80)
    print("\n📚 [로컬 Vector DB 안내 - 4대 데이터 카테고리 & 추천 질문]")
    print("--------------------------------------------------------------------------------")
    print("1. 💸 정책자금 및 금융상품 (PDF)")
    print("   - 데이터: 중소벤처기업부/소상공인시장진흥공단 정책자금 안내, 신용보증기금 보증상품 등")
    print("   - 💡 추천 질문: \"소상공인 정책자금 신청 자격과 제한 대상을 알려줘\"")
    print("   - 💡 추천 질문: \"신용보증기금의 보증상품 성과평가 결과를 요약해줘\"")
    print("\n2. 📊 상권 및 경영 데이터")
    print("   - 데이터: 소상공인시장진흥공단 상권정보 OpenAPI, KOSIS 국가통계포털 등")
    print("   - 💡 추천 질문: \"소상공인시장진흥공단의 상권정보 데이터 포맷은 어떻게 구성되어 있나요?\"")
    print("\n3. 📈 경기 및 소비 데이터")
    print("   - 데이터: 한국은행 ECOS 경제통계, 통계청 소비자물가지수, 카드 소비 등")
    print("   - 💡 추천 질문: \"전라남도 소비자물가지수 추이에 대해 설명해줘\"")
    print("\n4. 🛡️ 토스 KYC 연계 금융 규제 데이터")
    print("   - 데이터: 금융정보분석원(FIU) 고객확인제도(KYC) 지침, 금융위 AML 자료, 금감원 전자금융 가이드")
    print("   - 💡 추천 질문: \"비대면 가맹점 심사 시 고객확인제도(KYC) 필수 확인 항목은 무엇인가요?\"")
    print("   - 💡 추천 질문: \"전자금융업 감독규정상 자금세탁방지(AML) 내부통제 절차는 어떻게 되나요?\"")
    print("--------------------------------------------------------------------------------")
    print("💡 위 추천 질문들을 복사하여 바로 테스트해 보실 수 있습니다.")
    print("💡 로컬 DB에 없는 질문일 경우 실시간 웹 검색(DuckDuckGo)으로 보완합니다.")
    print("👉 종료하려면 'exit'을 입력하세요.\n")

    while True:
        query = input("🔍 질문을 입력하세요: ").strip()
        if not query:
            continue
        if query.lower() == 'exit':
            break

        # 그래프 실행
        initial_state = {"question": query, "documents": [], "web_search": False, "generation": "", "sources": []}
        try:
            result = app.invoke(initial_state)
            
            print("\n" + "="*40 + " [ 에이전트 답변 ] " + "="*40)
            print(result["generation"])
            print("="*96)
            
            # 검색 및 출처 요약
            if result.get("sources"):
                print("\n📌 참고 출처:")
                for src in result["sources"]:
                    print(f"- {src}")
            else:
                print("\n📌 참고 출처: 로컬 DB 및 웹 검색 결과 없음 (자체 지식 기반 답변)")
                
        except Exception as e:
            print(f"❌ 에러 발생: {e}")
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()

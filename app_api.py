import os
import sys
import importlib.util
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# 1. 3.qa.py 모듈 동적 로드 (파일명 시작이 숫자여서 일반 import가 불가함)
current_dir = os.path.dirname(os.path.abspath(__file__))
qa_script_path = os.path.join(current_dir, "3.qa.py")

if not os.path.exists(qa_script_path):
    raise FileNotFoundError(f"3.qa.py 파일을 찾을 수 없습니다: {qa_script_path}")

print("[Start] 3.qa.py load & LangGraph Agent init...")
spec = importlib.util.spec_from_file_location("qa_agent", qa_script_path)
qa_agent = importlib.util.module_from_spec(spec)
sys.modules["qa_agent"] = qa_agent
spec.loader.exec_module(qa_agent)
print("[Success] LangGraph Agent init done!")

# 2. FastAPI 앱 및 CORS 설정
app = FastAPI(title="Safe-Trade & Small-business Financial AI Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 편의를 위해 전체 허용 (배포 시 변경 권장)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 요청/응답 스키마 정의
class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    generation: str
    sources: List[str]

# 4. API 라우트 정의
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="질문을 입력해 주세요.")
    
    # LangGraph 실행 상태 초기화
    initial_state = {
        "question": question,
        "documents": [],
        "web_search": False,
        "generation": "",
        "sources": []
    }
    
    try:
        # 3.qa.py에서 컴파일한 graph app을 호출합니다.
        result = qa_agent.app.invoke(initial_state)
        
        return ChatResponse(
            generation=result.get("generation", ""),
            sources=result.get("sources", [])
        )
    except Exception as e:
        print(f"❌ API 에러 발생: {e}")
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str:
            friendly_msg = (
                "⚠️ 현재 일시적으로 Gemini API 호출 한도(무료 등급)가 초과되었습니다.\n"
                "약 10~20초 뒤에 다시 시도해 주시면 정상적으로 답변을 받아보실 수 있습니다."
            )
            return ChatResponse(
                generation=friendly_msg,
                sources=[]
            )
        
        return ChatResponse(
            generation=f"⚠️ 서비스 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.\n(상세 내용: {err_str})",
            sources=[]
        )

# 5. 로컬 테스트용
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app_api:app", host="0.0.0.0", port=port, reload=False)

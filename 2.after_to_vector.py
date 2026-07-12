import os
import re
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, CSVLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

# Optional dependencies for Excel and HWP
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import olefile
    import zlib
except ImportError:
    olefile = None

def extract_hwp_text(filepath: str) -> str:
    """
    HWP 파일(.hwp)에서 순수 텍스트만 추출하는 함수입니다.
    olefile 라이브러리를 사용하여 HWP 파일 내부의 압축된 구조(PrvText, BodyText 등)에 접근해 텍스트를 뽑아냅니다.
    """
    if olefile is None:
        return "[Error] olefile 패키지가 없습니다."
    try:
        f = olefile.OleFileIO(filepath)
        dirs = f.listdir()
        if ['PrvText'] in dirs:
            prv_text = f.openstream('PrvText').read()
            return prv_text.decode('utf-16le', errors='ignore')
        
        text = ""
        for d in dirs:
            if d[0] == 'BodyText':
                stream = f.openstream(d).read()
                try:
                    decompressed = zlib.decompress(stream, -15)
                    text += decompressed.decode('utf-16le', errors='ignore')
                except Exception:
                    pass
        return text if text else "HWP 텍스트 추출에 실패했습니다."
    except Exception as e:
        return f"[Error] HWP 파일 읽기 실패: {str(e)}"

class HWPLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    def load(self) -> List[Document]:
        text = extract_hwp_text(self.file_path)
        return [Document(page_content=text, metadata={"source": self.file_path})]

def process_excel(file_path: str) -> List[Document]:
    """
    엑셀 파일(.xls, .xlsx)을 읽어서 각 행(Row) 단위 데이터를 
    하나의 LangChain Document(문서) 객체로 변환합니다.
    """
    if pd is None:
        return []
    docs = []
    try:
        df = pd.read_excel(file_path)
        if len(df) > 20:
            print(f"⚠️ 대형 Excel 파일 감지 ({len(df)}행). 첫 20행만 샘플링합니다: {file_path}")
            df = df.head(20)
        for index, row in df.iterrows():
            content = "\n".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
            docs.append(Document(page_content=content, metadata={"source": file_path, "row": index}))
    except Exception:
        pass
    return docs

def load_document(file_path: str) -> List[Document]:
    """
    파일의 확장자를 확인한 뒤, 각 포맷에 맞는 적절한 로더(Loader)를 사용해 데이터를 읽어옵니다.
    - 지원 포맷: PDF, CSV, Excel, HWP, TXT/MD
    """
    ext = os.path.splitext(file_path)[-1].lower()
    filename = os.path.basename(file_path).lower()
    
    # 1. Skip CSV and Excel files entirely (raw data datasets, not needed for general text QA)
    if ext in ['.csv', '.xls', '.xlsx']:
        return []
        
    # 2. Skip template/form files (only contain blank forms and empty guidelines, not actual knowledge)
    if any(keyword in filename for keyword in ["별첨", "동의서", "지원서", "계획서", "서식", "신청서", "확약서"]):
        return []

    try:
        if ext == '.pdf':
            return PyPDFLoader(file_path).load()
        elif ext in ['.hwp', '.hwpx']:
            return HWPLoader(file_path).load()
        elif ext in ['.txt', '.md']:
            try:
                return TextLoader(file_path, encoding='utf-8').load()
            except UnicodeDecodeError:
                return TextLoader(file_path, encoding='cp949').load()
    except Exception as e:
        print(f"❌ 파일 로드 실패 [{file_path}]: {e}")
    return []

def main():
    data_dir = "Data"
    db_dir = "./chroma_db"
    
    if not os.path.exists(data_dir):
        print(f"📁 '{data_dir}' 폴더가 없습니다.")
        return
        
    print(f"🔍 '{data_dir}' 폴더 내 문서 로딩 중...")
    all_documents = []
    for root, _, files in os.walk(data_dir):
        for file in files:
            file_path = os.path.join(root, file)
            docs = load_document(file_path)
            all_documents.extend(docs)
            
    if not all_documents:
        print("읽어들일 문서가 없습니다.")
        return
        
    print(f"✅ 총 {len(all_documents)} 페이지 로딩 완료. Chunking을 시작합니다.")
    
    # 텍스트 스플리터 설정
    # LLM이 한 번에 읽을 수 있는 문장 길이에 한계가 있으므로, 
    # 긴 문서를 지정된 크기(chunk_size)로 자릅니다.
    # 이때 문맥이 뚝 끊기지 않도록 앞뒤로 일정 글자 수(chunk_overlap)만큼 겹치게 설정합니다.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200000,
        chunk_overlap=5000,
        length_function=len
    )
    chunks = text_splitter.split_documents(all_documents)
    print(f"✅ 총 {len(chunks)}개의 Chunk 생성 완료.")

    # 임베딩(Embedding) 모델 로드
    # Render 무료 티어(512MB RAM) 환경에서 OOM 방지를 위해 가벼운 Gemini API 임베딩을 사용합니다.
    print("\n🧠 임베딩 모델(Gemini API)을 로드하는 중입니다...")
    
    # .env에서 모든 API 키를 수집합니다 (GEMINI_API_KEY, GEMINI_API_KEY_2, ...)
    api_keys = []
    env_path = "./.env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip().startswith("GEMINI_API_KEY") or k.strip() == "GOOGLE_API_KEY":
                        key_val = v.strip().strip("'").strip('"')
                        if key_val and key_val not in api_keys:
                            api_keys.append(key_val)
    
    # 환경변수에서도 추가 수집
    for env_name in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY_2"]:
        env_val = os.environ.get(env_name)
        if env_val and env_val not in api_keys:
            api_keys.append(env_val)
    
    if not api_keys:
        print("❌ API 키를 찾을 수 없습니다. .env 파일을 확인해 주세요.")
        return
    
    print(f"🔑 총 {len(api_keys)}개의 API 키를 발견했습니다.")
    
    current_key_idx = 0
    api_key = api_keys[current_key_idx]
    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key
    
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    print("\n💾 Chroma DB에 벡터 데이터를 저장합니다...")
    # Tokenizer 에러 방지를 위해 page_content가 완벽한 문자열인지 다시 한 번 검증 및 필터링
    # PDF에서 추출된 텍스트 중 깨진 유니코드(서로게이트 문자, Private Use Area 문자)를 제거합니다.
    valid_chunks = []
    for c in chunks:
        if c.page_content is not None:
            text = str(c.page_content).strip()
            # 서로게이트 문자(\ud800-\udfff) 및 Private Use Area 문자(\ue000-\uf8ff) 제거
            text = re.sub(r'[\ud800-\udfff\ue000-\uf8ff\U000F0000-\U000FFFFF]', '', text)
            text = text.strip()
            if len(text) > 5: # 빈 문자열이나 너무 짧은 노이즈 데이터 제외
                c.page_content = text
                valid_chunks.append(c)
    
    print(f"🧹 전처리 후 유효한 Chunk: {len(valid_chunks)}개 (기존 {len(chunks)}개)")

    import time
    batch_size = 15
    max_retries = 8
    vectorstore = None
    total_chunks = len(valid_chunks)
    for i in range(0, total_chunks, batch_size):
        batch_chunks = valid_chunks[i:i + batch_size]
        batch_end = min(i + batch_size, total_chunks)
        print(f"[{i+1} ~ {batch_end}] 배치 저장 중... ({batch_end}/{total_chunks}, {batch_end*100//total_chunks}%)")
        
        for attempt in range(max_retries):
            try:
                if vectorstore is None:
                    vectorstore = Chroma.from_documents(
                        documents=batch_chunks,
                        embedding=embeddings,
                        persist_directory=db_dir
                    )
                else:
                    vectorstore.add_documents(batch_chunks)
                break  # 성공 시 루프 탈출
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    # 다른 API 키가 남아 있으면 즉시 전환
                    if current_key_idx + 1 < len(api_keys):
                        current_key_idx += 1
                        api_key = api_keys[current_key_idx]
                        os.environ["GEMINI_API_KEY"] = api_key
                        os.environ["GOOGLE_API_KEY"] = api_key
                        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
                        print(f"🔄 API 키 #{current_key_idx + 1}로 전환합니다. 즉시 재시도...")
                        continue
                    wait_time = (2 ** attempt) * 10  # 10, 20, 40, 80초 지수 백오프
                    print(f"⏳ API 할당량 초과. {wait_time}초 대기 후 재시도합니다... (시도 {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"❌ 예상치 못한 에러: {e}")
                    print("이 배치를 건너뛰고 계속 진행합니다.")
                    break
        else:
            print(f"⚠️ 최대 재시도 횟수 초과. [{i+1} ~ {batch_end}] 배치를 건너뜁니다.")
        
        # 배치 간 딜레이 (100 RPM 제한 방지)
        time.sleep(12)
    
    print(f"\n🎉 [SUCCESS] 모든 임베딩이 성공적으로 완료되었습니다!")
    print(f"저장된 Vector DB 경로: {os.path.abspath(db_dir)}")
    print("이제 3번 스크립트를 통해 검색(Retriever) 및 질문(QA) 테스트를 진행할 수 있습니다.")

if __name__ == "__main__":
    main()

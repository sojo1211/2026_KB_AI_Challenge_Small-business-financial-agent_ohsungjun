import os
import re
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, CSVLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
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
    try:
        if ext == '.pdf':
            return PyPDFLoader(file_path).load()
        elif ext == '.csv':
            try:
                # pandas를 활용한 더 안정적인 CSV 파싱 (인코딩 자동 감지 및 에러 무시)
                if pd is None:
                    return CSVLoader(file_path, encoding='utf-8').load()
                    
                docs = []
                try:
                    df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
                except UnicodeDecodeError:
                    try:
                        df = pd.read_csv(file_path, encoding='cp949', on_bad_lines='skip')
                    except UnicodeDecodeError:
                        df = pd.read_csv(file_path, encoding='euc-kr', on_bad_lines='skip')
                
                for index, row in df.iterrows():
                    content = "\n".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
                    docs.append(Document(page_content=content, metadata={"source": file_path, "row": index}))
                return docs
            except Exception as e:
                print(f"CSV 파싱 중 에러 발생 (스킵): {e}")
                return []
        elif ext in ['.xls', '.xlsx']:
            return process_excel(file_path)
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
        chunk_size=2000,
        chunk_overlap=300,
        length_function=len
    )
    chunks = text_splitter.split_documents(all_documents)
    print(f"✅ 총 {len(chunks)}개의 Chunk 생성 완료.")

    # 임베딩(Embedding) 모델 로드
    # multilingual-e5-small: 다국어(한국어 포함) 지원, 470MB로 가볍고 빠름
    print("\n🧠 임베딩 모델(multilingual-e5-small)을 로드하는 중입니다...")
    
    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-small",
        model_kwargs={'device': 'cuda'},
        encode_kwargs={'normalize_embeddings': True, 'batch_size': 128}
    )

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

    # 한 번에 너무 많은 데이터를 넣으면 메모리 에러나 tokenizer 제한이 발생할 수 있으므로, 안전하게 추가
    batch_size = 5000
    vectorstore = None
    for i in range(0, len(valid_chunks), batch_size):
        batch_chunks = valid_chunks[i:i + batch_size]
        print(f"[{i+1} ~ {min(i+batch_size, len(valid_chunks))}] 배치 저장 중...")
        try:
            if vectorstore is None:
                vectorstore = Chroma.from_documents(
                    documents=batch_chunks,
                    embedding=embeddings,
                    persist_directory=db_dir
                )
            else:
                vectorstore.add_documents(batch_chunks)
        except TypeError as e:
            print("❌ 배치 저장 중 TypeError 발생. 문제가 되는 청크를 찾기 위해 하나씩 저장합니다...")
            for idx, doc in enumerate(batch_chunks):
                try:
                    if vectorstore is None:
                        vectorstore = Chroma.from_documents(documents=[doc], embedding=embeddings, persist_directory=db_dir)
                    else:
                        vectorstore.add_documents([doc])
                except Exception as inner_e:
                    print(f"🚨 에러를 유발한 문서 [Index: {i + idx}] 🚨")
                    print("--- [문서 내용 시작] ---")
                    print(repr(doc.page_content))
                    print("--- [문서 내용 끝] ---")
                    print(f"메타데이터: {doc.metadata}")
                    print(f"발생 에러: {inner_e}")
                    print("이 문서를 건너뛰고 계속 진행합니다.")
    
    print(f"\n🎉 [SUCCESS] 모든 임베딩이 성공적으로 완료되었습니다!")
    print(f"저장된 Vector DB 경로: {os.path.abspath(db_dir)}")
    print("이제 3번 스크립트를 통해 검색(Retriever) 및 질문(QA) 테스트를 진행할 수 있습니다.")

if __name__ == "__main__":
    main()

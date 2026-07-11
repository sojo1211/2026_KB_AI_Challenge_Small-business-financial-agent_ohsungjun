import os
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader, 
    CSVLoader, 
    TextLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

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
    """간단한 HWP 텍스트 추출 함수 (olefile 사용)"""
    if olefile is None:
        return "[Error] olefile 패키지가 설치되지 않았습니다. 'pip install olefile'을 실행하세요."
    
    try:
        f = olefile.OleFileIO(filepath)
        dirs = f.listdir()
        
        # 1. PrvText (미리보기 텍스트) 스트림이 있는 경우 (가장 깨끗한 텍스트)
        if ['PrvText'] in dirs:
            prv_text = f.openstream('PrvText').read()
            return prv_text.decode('utf-16le', errors='ignore')
        
        # 2. BodyText 스트림에서 텍스트 추출 (태그가 일부 포함될 수 있음)
        text = ""
        for d in dirs:
            if d[0] == 'BodyText':
                stream = f.openstream(d).read()
                try:
                    # zlib 압축 해제 (-15는 헤더가 없는 raw deflate를 의미)
                    decompressed = zlib.decompress(stream, -15)
                    text += decompressed.decode('utf-16le', errors='ignore')
                except Exception:
                    pass
        return text if text else "HWP 텍스트 추출에 실패했거나 문서가 비어있습니다."
    except Exception as e:
        return f"[Error] HWP 파일 읽기 실패: {str(e)}"

class HWPLoader:
    """LangChain용 Custom HWP Loader"""
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    def load(self) -> List[Document]:
        text = extract_hwp_text(self.file_path)
        return [Document(page_content=text, metadata={"source": self.file_path})]

def process_excel(file_path: str) -> List[Document]:
    """Pandas를 이용한 엑셀(Excel) 파싱 헬퍼"""
    if pd is None:
        return [Document(page_content="[Error] pandas가 설치되지 않았습니다. 'pip install pandas openpyxl'을 실행하세요.", metadata={"source": file_path})]
    
    docs = []
    try:
        df = pd.read_excel(file_path)
        # 각 행(Row)을 하나의 Document로 변환
        for index, row in df.iterrows():
            content = "\n".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
            docs.append(Document(page_content=content, metadata={"source": file_path, "row": index}))
    except Exception as e:
        docs.append(Document(page_content=f"엑셀 읽기 에러: {str(e)}", metadata={"source": file_path}))
    return docs

def load_document(file_path: str) -> List[Document]:
    """파일 확장자에 따라 적절한 Loader를 연결하는 라우터 함수"""
    ext = os.path.splitext(file_path)[-1].lower()
    
    try:
        if ext == '.pdf':
            loader = PyPDFLoader(file_path)
            return loader.load()
        elif ext == '.csv':
            # 인코딩 에러 방지 및 포맷 불량 방지를 위해 pandas 기반 파싱 적용
            try:
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
            loader = HWPLoader(file_path)
            return loader.load()
        elif ext in ['.txt', '.md']:
            try:
                loader = TextLoader(file_path, encoding='utf-8')
                return loader.load()
            except UnicodeDecodeError:
                loader = TextLoader(file_path, encoding='cp949')
                return loader.load()
        else:
            print(f"⚠️ 지원하지 않는 확장자입니다 (스킵): {file_path}")
            return []
    except Exception as e:
        print(f"❌ 파일 로드 실패 [{file_path}]: {e}")
        return []

def main():
    data_dir = "Data"
    if not os.path.exists(data_dir):
        print(f"📁 '{data_dir}' 폴더가 없습니다. 스크립트와 동일한 위치에 폴더를 만들어주세요.")
        return
        
    print(f"🔍 '{data_dir}' 폴더 내의 모든 문서 파일들을 탐색합니다...\n")
    all_documents = []
    
    # 폴더 내 모든 파일 재귀적 탐색
    for root, _, files in os.walk(data_dir):
        for file in files:
            file_path = os.path.join(root, file)
            print(f"📄 읽는 중: {file_path}")
            docs = load_document(file_path)
            all_documents.extend(docs)
            
    print(f"\n✅ 파일 로딩 완료! 총 {len(all_documents)}개의 페이지/행(Row)을 읽어들였습니다.")
    
    if not all_documents:
        print("읽어들일 문서가 없습니다. Data 폴더 안에 파일을 넣어주세요.")
        return
        
    print("\n✂️  문서 분할(Chunking)을 시작합니다...")
    # Chunking 설정 (1000글자 단위로 자르되, 앞뒤 200글자씩 겹치도록 설정하여 문맥 유실 방지)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    
    chunks = text_splitter.split_documents(all_documents)
    print(f"✅ Chunking 완료! 총 {len(chunks)}개의 벡터용 데이터 조각(Chunk)이 생성되었습니다.")
    
    # 첫 번째 청크 미리보기
    if chunks:
        print("\n--- 🔎 첫 번째 Chunk 미리보기 (최대 300자) ---")
        print(chunks[0].page_content[:300])
        print("-------------------------------------------------")
        print(f"메타데이터: {chunks[0].metadata}")

    print("\n🚀 [완료] 이 Chunk들을 ChromaDB에 임베딩할 준비가 모두 끝났습니다!")

if __name__ == "__main__":
    main()

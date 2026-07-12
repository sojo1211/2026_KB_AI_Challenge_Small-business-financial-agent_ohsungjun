import os
import time
import sys
import re
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, CSVLoader, TextLoader

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
    if pd is None:
        return []
    docs = []
    try:
        df = pd.read_excel(file_path)
        if len(df) > 500:
            print(f"⚠️ 대형 Excel 파일 감지 ({len(df)}행). 첫 500행만 샘플합니다: {file_path}")
            df = df.head(500)
        for index, row in df.iterrows():
            content = "\n".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
            docs.append(Document(page_content=content, metadata={"source": file_path, "row": index}))
    except Exception:
        pass
    return docs

def load_document(file_path: str) -> List[Document]:
    ext = os.path.splitext(file_path)[-1].lower()
    try:
        if ext == '.pdf':
            return PyPDFLoader(file_path).load()
        elif ext == '.csv':
            try:
                if pd is None:
                    return CSVLoader(file_path, encoding='utf-8').load()
                docs = []
                file_size = os.path.getsize(file_path)
                nrows_to_read = 500
                if file_size > 1 * 1024 * 1024:
                    print(f"⚠️ 대형 CSV 파일 감지 ({file_size / 1024 / 1024:.2f}MB). 첫 {nrows_to_read}행만 로드합니다: {file_path}")
                try:
                    df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip', nrows=nrows_to_read)
                except UnicodeDecodeError:
                    try:
                        df = pd.read_csv(file_path, encoding='cp949', on_bad_lines='skip', nrows=nrows_to_read)
                    except UnicodeDecodeError:
                        df = pd.read_csv(file_path, encoding='euc-kr', on_bad_lines='skip', nrows=nrows_to_read)
                
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
    if not os.path.exists(data_dir):
        print("Data dir not found")
        return
        
    print("Testing document loading...")
    all_docs = []
    for root, _, files in os.walk(data_dir):
        for file in files:
            file_path = os.path.join(root, file)
            t0 = time.time()
            docs = load_document(file_path)
            t1 = time.time()
            all_docs.extend(docs)
            print(f"Loaded: {file} ({len(docs)} docs, {t1-t0:.2f}s)")
            
    print(f"Total documents: {len(all_docs)}")

if __name__ == "__main__":
    main()

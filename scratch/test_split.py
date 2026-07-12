import os
import re
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, CSVLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

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
        pass
    return []

def main():
    data_dir = "Data"
    all_documents = []
    for root, _, files in os.walk(data_dir):
        for file in files:
            file_path = os.path.join(root, file)
            docs = load_document(file_path)
            all_documents.extend(docs)
            
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=10000,
        chunk_overlap=1000,
        length_function=len
    )
    chunks = text_splitter.split_documents(all_documents)
    print(f"Total documents: {len(all_documents)}")
    print(f"Total chunks generated: {len(chunks)}")

    # let's also filter chunks like in 2.after_to_vector.py
    valid_chunks = []
    for c in chunks:
        if c.page_content is not None:
            text = str(c.page_content).strip()
            text = re.sub(r'[\ud800-\udfff\ue000-\uf8ff\U000F0000-\U000FFFFF]', '', text)
            text = text.strip()
            if len(text) > 5:
                c.page_content = text
                valid_chunks.append(c)
    print(f"Valid chunks count: {len(valid_chunks)}")

if __name__ == "__main__":
    main()

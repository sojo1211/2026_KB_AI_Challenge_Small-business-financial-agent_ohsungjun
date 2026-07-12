import os
import time
from langchain_community.document_loaders import PyPDFLoader

pdf_path = r"Data\4.토스 KYC와 연결하기 위해 추가하면 좋은 데이터(PDF)\4-3.금융감독원\자금세탁방지_내부통제_가이드라인(25.8월).pdf"
if os.path.exists(pdf_path):
    print(f"File exists: {pdf_path}, size={os.path.getsize(pdf_path)}")
    t0 = time.time()
    try:
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        print(f"Loaded successfully! Pages: {len(docs)}, time: {time.time()-t0:.2f}s")
    except Exception as e:
        print(f"Error loading: {e}")
else:
    print(f"File not found: {pdf_path}")

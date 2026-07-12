import os
import time
from langchain_google_genai import GoogleGenerativeAIEmbeddings

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not api_key:
    env_path = "./.env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
                        api_key = v.strip().strip("'").strip('"')
                        break

os.environ["GOOGLE_API_KEY"] = api_key
os.environ["GEMINI_API_KEY"] = api_key

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

# Test batch sizes
for size in [5, 10, 20, 50, 100]:
    texts = [f"This is a test document number {i}" for i in range(size)]
    t0 = time.time()
    try:
        res = embeddings.embed_documents(texts)
        print(f"Batch size {size}: Success! Vector length: {len(res)}, time: {time.time()-t0:.2f}s")
    except Exception as e:
        print(f"Batch size {size}: Failed! Error: {e}")
    time.sleep(2)

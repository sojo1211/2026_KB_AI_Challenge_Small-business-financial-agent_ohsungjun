import os
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

print(f"API key loaded: {api_key[:10]}...")
os.environ["GOOGLE_API_KEY"] = api_key
os.environ["GEMINI_API_KEY"] = api_key

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
print("Embedding 'test string'...")
res = embeddings.embed_query("test string")
print(f"Success! Vector length: {len(res)}")

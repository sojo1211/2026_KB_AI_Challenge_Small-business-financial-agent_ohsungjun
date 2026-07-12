import os
import time
from google import genai

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

client = genai.Client(api_key=api_key)

# We know models/gemini-embedding-001 is available
model_name = "models/gemini-embedding-001"

# Test batch sizes using the native client
for size in [50, 100]:
    texts = [f"This is a test document number {i} with some generic content to embed" for i in range(size)]
    t0 = time.time()
    try:
        response = client.models.embed_content(
            model=model_name,
            contents=texts
        )
        # response.embeddings is a list of Embedding objects
        embs = response.embeddings
        print(f"Native Batch size {size}: Success! Vector count: {len(embs)}, first dim: {len(embs[0].values)}, time: {time.time()-t0:.2f}s")
    except Exception as e:
        print(f"Native Batch size {size}: Failed! Error: {e}")
    time.sleep(2)

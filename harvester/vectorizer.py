import os, requests, weaviate
from tqdm import tqdm

client = weaviate.Client(os.environ["WEAVIATE_URL"])
OLLAMA_URL = os.getenv("EMBEDDER_URL", "http://192.168.1.156:11535/api/embeddings")
MODEL_NAME = os.getenv("MODEL_NAME", "nomic-embed-text")

def push_to_weaviate(docs, lang, version):
    for doc in tqdm(docs, desc=f"Ingesting {lang}@{version}"):
        r = requests.post(OLLAMA_URL, json={"model": MODEL_NAME, "input": doc["text"][:8000]})
        embedding = r.json().get("embedding", [])
        data = {
            "text": doc["text"],
            "lang": lang,
            "version": version,
            "source": doc["source"],
        }
        client.data_object.create(data, "Documentation", vector=embedding)

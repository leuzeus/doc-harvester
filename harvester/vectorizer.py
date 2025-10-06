import os, requests, weaviate
from tqdm import tqdm

client = weaviate.Client(os.environ["WEAVIATE_URL"])
OLLAMA_URL = os.getenv("EMBEDDER_URL", "http://192.168.1.156:11535/api/embeddings")
MODEL_NAME = os.getenv("MODEL_NAME", "nomic-embed-text")

def push_to_weaviate(docs, lang, version):
    for doc in tqdm(docs, desc=f"Ingesting {lang}@{version}"):
        payload = {"model": MODEL_NAME, "input": doc["text"][:8000]}
        try:
            r = requests.post(OLLAMA_URL, json=payload)
            r.raise_for_status()
            embedding = r.json().get("embedding")
            if embedding is None:
                # skip si embed non fourni
                continue
        except Exception as e:
            print(f"Embedding failed for {doc['source']}: {e}")
            continue

        data = {
            "text": doc["text"],
            "lang": lang,
            "version": version,
            "source": doc["source"],
        }
        try:
            client.data_object.create(data, "Documentation", vector=embedding)
        except Exception as e:
            print(f"Weaviate insertion failed for {doc['source']}: {e}")
            continue

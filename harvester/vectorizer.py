import os
import requests
from weaviate import connect, WeaviateClient
from weaviate.connect import ConnectionParams
from tqdm import tqdm

# Exemple d'initialisation avec v4
def get_weaviate_client():
    weaviate_url = os.environ["WEAVIATE_URL"]  # ex: "http://weaviate:8080"
    # On suppose que le grpc port est 50051 (par défaut pour Weaviate)
    # Si tu l’as mappé dans Docker compose, ça doit être exposé.
    conn = ConnectionParams.from_url(weaviate_url, grpc_port=50051)
    client = WeaviateClient(conn, skip_init_checks=False)
    return client

client = get_weaviate_client()

OLLAMA_URL = os.getenv("EMBEDDER_URL", "http://127.0.0.1:11434/api/embeddings")
MODEL_NAME = os.getenv("MODEL_NAME", "nomic-embed-text")

def push_to_weaviate(docs, lang, version):
    # On peut utiliser batch pour insertion efficace
    with client.batch.dynamic() as batch:
        for doc in tqdm(docs, desc=f"Ingesting {lang}@{version}"):
            payload = {"model": MODEL_NAME, "input": doc["text"][:8000]}
            try:
                r = requests.post(OLLAMA_URL, json=payload)
                r.raise_for_status()
                embedding = r.json().get("embedding")
                if embedding is None:
                    continue
            except Exception as e:
                print(f"Embedding failed for {doc['source']}: {e}")
                continue

            properties = {
                "text": doc["text"],
                "lang": lang,
                "version": version,
                "source": doc["source"],
            }
            try:
                batch.add_object(properties=properties, class_name="Documentation", vector=embedding)
            except Exception as e:
                print(f"Weaviate insertion failed for {doc['source']}: {e}")
                continue

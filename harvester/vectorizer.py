import os
import requests
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.exceptions import WeaviateClosedClientError
from tqdm import tqdm

_client = None

def _init_client():
    # Lecture des variables d’environnement
    http_host = os.getenv("WEAVIATE_HOST", "weaviate")
    http_port = int(os.getenv("WEAVIATE_PORT", 8080))
    grpc_host = http_hos
    grpc_port = int(os.getenv("WEAVIATE_GRPC_PORT", 50051))
    http_secure = os.getenv("WEAVIATE_HTTP_SECURE", "false").lower() == "true"
    grpc_secure = os.getenv("WEAVIATE_GRPC_SECURE", "false").lower() == "true"

    conn = ConnectionParams.from_params(
        http_host=http_host,
        http_port=http_port,
        http_secure=http_secure,
        grpc_host=grpc_host,
        grpc_port=grpc_port,
        grpc_secure=grpc_secure
    )
    client = WeaviateClient(conn, skip_init_checks=False)
    client.connect()
    return client

def get_client():
    global _client
    if _client is None:
        _client = _init_client()
    else:
        # vérification de connexion
        try:
            _client.is_ready()
        except Exception:
            try:
                _client.connect()
            except Exception:
                _client = _init_client()
    return _client

OLLAMA_URL = os.getenv("EMBEDDER_URL", "http://192.168.1.156:11535/api/embeddings")
MODEL_NAME = os.getenv("MODEL_NAME", "nomic-embed-text")

def push_to_weaviate(docs, lang, version):
    client = get_client()
    try:
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
                    print(f"Embedding failed for {doc.get('source')}: {e}")
                    continue

                properties = {
                    "text": doc["text"],
                    "lang": lang,
                    "version": version,
                    "source": doc.get("source"),
                }
                try:
                    batch.add_object(properties=properties, class_name="Documentation", vector=embedding)
                except Exception as e:
                    print(f"Weaviate insertion failed for {doc.get('source')}: {e}")
                    continue
    except WeaviateClosedClientError:
        # En cas de client fermé, réinitialiser et réessayer
        client = _init_client()
        with client.batch.dynamic() as batch:
            for doc in tqdm(docs, desc=f"Ingesting {lang}@{version} [retry]"):
                payload = {"model": MODEL_NAME, "input": doc["text"][:8000]}
                try:
                    r = requests.post(OLLAMA_URL, json=payload)
                    r.raise_for_status()
                    embedding = r.json().get("embedding")
                    if embedding is None:
                        continue
                except Exception as e:
                    print(f"Embedding failed (retry) for {doc.get('source')}: {e}")
                    continue

                properties = {
                    "text": doc["text"],
                    "lang": lang,
                    "version": version,
                    "source": doc.get("source"),
                }
                try:
                    batch.add_object(properties=properties, class_name="Documentation", vector=embedding)
                except Exception as e:
                    print(f"Weaviate insertion failed (retry) for {doc.get('source')}: {e}")
                    continue

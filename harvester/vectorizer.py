import os
import requests
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.exceptions import WeaviateClientClosedError
from tqdm import tqdm

_client = None

def _init_client():
    # extraire les variables d’environnement
    http_host = os.getenv("WEAVIATE_HOST", "weaviate")
    http_port = int(os.getenv("WEAVIATE_PORT", 8080))
    grpc_host = http_host
    grpc_port = int(os.getenv("WEAVIATE_GRPC_PORT", 50051))

    conn = ConnectionParams(
        http_host=http_host,
        http_port=http_port,
        grpc_host=grpc_host,
        grpc_port=grpc_port,
        # selon besoin tu peux mettre secure flags
        # grpc_secure = False, http_secure = False, etc.
    )
    client = WeaviateClient(conn, skip_init_checks=False)
    client.connect()
    return client

def get_client():
    global _client
    if _client is None:
        _client = _init_client()
    else:
        # tenter de vérifier l’état
        try:
            # is_ready() est une méthode légère de contrôle (ou une autre méthode selon version)
            _client.is_ready()
        except Exception:
            try:
                _client.connect()
            except Exception:
                # recréer client si nécessaire
                _client = _init_client()
    return _client

OLLAMA_URL = os.getenv("EMBEDDER_URL", "http://127.0.0.1:11434/api/embeddings")
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
    except WeaviateClientClosedError:
        # si le client est fermé, on reconnecte et réessaye
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

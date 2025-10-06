import os
import requests
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.exceptions import WeaviateClosedClientError
from tqdm import tqdm

_client = None

def _init_client():
    http_host = os.getenv("WEAVIATE_HOST", "weaviate")
    http_port = int(os.getenv("WEAVIATE_PORT", 8080))
    grpc_host = http_host
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
        try:
            _client.is_ready()
        except Exception as e:
            print(f"DEBUG: client.is_ready() raised {e}, reconnecting client")
            try:
                _client.connect()
            except Exception as e2:
                print(f"DEBUG: reconnect failed: {e2}, reinitializing client")
                _client = _init_client()
    return _client

OLLAMA_URL = os.getenv("EMBEDDER_URL", "http://127.0.0.1:11434/api/embeddings")
MODEL_NAME = os.getenv("MODEL_NAME", "nomic-embed-text")

def push_to_weaviate(docs, lang, version):
    client = get_client()
    print(f"DEBUG: Starting push_to_weaviate, lang={lang}, version={version}, num_docs={len(docs)}")

    try:
        with client.batch.dynamic() as batch:
            for i, doc in enumerate(docs):
                # Log du document
                print(f"DEBUG: Processing doc #{i}: source={doc.get('source')}, text_len={len(doc.get('text',''))}")

                payload = {
                    "model": MODEL_NAME,
                    "input": doc["text"][:8000]
                }
                try:
                    r = requests.post(OLLAMA_URL, json=payload)
                    r.raise_for_status()
                    embedding = r.json().get("embedding")
                    print(f"DEBUG: Received embedding type {type(embedding)}, length {len(embedding) if embedding else None}")
                    if embedding is None:
                        print("DEBUG: embedding is None, skipping this doc")
                        continue
                except Exception as e:
                    print(f"ERROR: embedding request failed for {doc.get('source')}: {e}")
                    continue

                properties = {
                    "text": doc["text"],
                    "lang": lang,
                    "version": version,
                    "source": doc.get("source")
                }
                print(f"DEBUG: Adding object with properties: {properties}")

                try:
                    batch.add_object(properties=properties, class_name="Documentation", vector=embedding)
                except Exception as e:
                    print(f"ERROR: batch.add_object failed for {doc.get('source')}: {e}")

    except WeaviateClosedClientError as e:
        print(f"ERROR: Weaviate client closed: {e}, retrying a new client")
        client = _init_client()
        with client.batch.dynamic() as batch:
            for i, doc in enumerate(docs):
                print(f"DEBUG RETRY: Processing doc #{i}: source={doc.get('source')}")
                payload = {
                    "model": MODEL_NAME,
                    "input": doc["text"][:8000]
                }
                try:
                    r = requests.post(OLLAMA_URL, json=payload)
                    r.raise_for_status()
                    embedding = r.json().get("embedding")
                    if embedding is None:
                        continue
                except Exception as e:
                    print(f"ERROR RETRY: embedding failed for {doc.get('source')}: {e}")
                    continue

                properties = {
                    "text": doc["text"],
                    "lang": lang,
                    "version": version,
                    "source": doc.get("source")
                }
                try:
                    batch.add_object(properties=properties, class_name="Documentation", vector=embedding)
                except Exception as e:
                    print(f"ERROR RETRY: batch.add_object failed for {doc.get('source')}: {e}")

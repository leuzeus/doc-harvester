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
            print(f"DEBUG: client.is_ready() raised {e}, reconnecting")
            try:
                _client.connect()
            except Exception as e2:
                print(f"DEBUG: reconnect failed: {e2}, reinitializing client")
                _client = _init_client()
    return _client


# URL de l’API embedder (Ollama ou autre)
OLLAMA_URL = os.getenv("EMBEDDER_URL", "http://ollama:11434/api/embeddings")
MODEL_NAME = os.getenv("MODEL_NAME", "nomic-embed-text")


def push_to_weaviate(docs, lang, version):
    client = get_client()
    print(f"DEBUG: Starting push_to_weaviate, lang={lang}, version={version}, num_docs={len(docs)}")

    # Vérifie la version serveur pour diagnostic
    try:
        meta = requests.get(f"http://{os.getenv('WEAVIATE_HOST', 'weaviate')}:8080/v1/meta").json()
        print(f"DEBUG: Connected to Weaviate server version {meta.get('version')}")
    except Exception as e:
        print(f"WARNING: Could not fetch Weaviate version: {e}")

    try:
        with client.batch.dynamic() as batch:
            for i, doc in enumerate(docs):
                print(f"DEBUG: Processing doc #{i}: source={doc.get('source')}, text_len={len(doc.get('text', ''))}")

                payload = {"model": MODEL_NAME, "input": doc["text"][:8000]}
                try:
                    r = requests.post(OLLAMA_URL, json=payload)
                    r.raise_for_status()
                    embedding = r.json().get("embedding")

                    if not isinstance(embedding, list):
                        print(f"ERROR: embedding invalid for {doc.get('source')} (type={type(embedding)}), skipping")
                        continue
                    print(f"DEBUG: embedding length={len(embedding)}")
                except Exception as e:
                    print(f"ERROR: embedding request failed for {doc.get('source')}: {e}")
                    continue

                properties = {
                    "text": doc["text"],
                    "lang": lang,
                    "version": version,
                    "source": doc.get("source")
                }

                try:
                    batch.add_object(
                        collection="Documentation",
                        properties=properties,
                        vector=embedding
                    )
                    print(f"DEBUG: Added doc #{i} to batch")
                except Exception as e:
                    print(f"ERROR: batch.add_object failed for {doc.get('source')}: {e}")

    except WeaviateClosedClientError as e:
        print(f"ERROR: Weaviate client closed: {e}, retrying with new client")
        client = _init_client()
        with client.batch.dynamic() as batch:
            for i, doc in enumerate(docs):
                try:
                    payload = {"model": MODEL_NAME, "input": doc["text"][:8000]}
                    r = requests.post(OLLAMA_URL, json=payload)
                    r.raise_for_status()
                    embedding = r.json().get("embedding")

                    if not isinstance(embedding, list):
                        print(f"ERROR RETRY: invalid embedding for {doc.get('source')}, skipping")
                        continue

                    batch.add_object(
                        collection="Documentation",
                        properties={
                            "text": doc["text"],
                            "lang": lang,

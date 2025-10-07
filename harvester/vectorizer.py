import os
import requests
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.exceptions import WeaviateClosedClientError, WeaviateBaseError
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
            # Si le client n’est pas prêt, on tente une reconnexion ou une réinitialisation
            print(f"WARNING: weaviate client not ready ({e}), reconnecting")
            try:
                _client.connect()
            except Exception as e2:
                print(f"WARNING: reconnect failed ({e2}), reinitializing client")
                _client = _init_client()
    return _client

OLLAMA_URL = os.getenv("EMBEDDER_URL", "http://ollama:11434/api/embeddings")
MODEL_NAME = os.getenv("MODEL_NAME", "nomic-embed-text")

def fetch_embedding_from_ollama(text: str):
    """Appelle Ollama et retourne un vecteur embedding ou None si échec."""
    payload = {
        "model": MODEL_NAME,
        "prompt": text  # Utiliser "prompt", pas "input"
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"ERROR: Ollama request exception: {e}")
        return None

    try:
        resp = r.json()
    except ValueError as e:
        print(f"ERROR: cannot parse Ollama JSON response: {e} — raw: {r.text}")
        return None

    # Pour debug léger en prod, tu peux activer ce log
    # print("DEBUG: Ollama response:", resp)

    embedding = None
    if isinstance(resp.get("embedding"), list):
        embedding = resp["embedding"]
    elif isinstance(resp.get("embeddings"), list) and len(resp["embeddings"]) > 0:
        embedding = resp["embeddings"][0]

    return embedding

def push_to_weaviate(docs, lang, version):
    client = get_client()
    print(f"INFO: push_to_weaviate start: lang={lang}, version={version}, docs={len(docs)}")

    # (Optionnel) vérifier version serveur
    try:
        meta = requests.get(f"http://{os.getenv('WEAVIATE_HOST', 'weaviate')}:8080/v1/meta", timeout=10).json()
        print(f"INFO: weaviate server version = {meta.get('version')}")
    except Exception:
        pass  # ce n’est pas bloquant

    try:
        with client.batch.dynamic() as batch:
            for i, doc in enumerate(docs):
                src = doc.get("source")
                text = doc.get("text", "")
                # On pourrait filtrer ou sauter les docs vides / très courts
                if not text:
                    print(f"WARNING: skipping empty text, source={src}")
                    continue

                embedding = fetch_embedding_from_ollama(text[:8000])
                if not isinstance(embedding, list) or len(embedding) == 0:
                    print(f"WARNING: invalid embedding, skipping document: {src}")
                    continue

                properties = {
                    "text": text,
                    "lang": lang,
                    "version": version,
                    "source": src
                }

                try:
                    batch.add_object(
                        collection="Documentation",
                        properties=properties,
                        vector=embedding
                    )
                except WeaviateBaseError as e:
                    # erreur locale d’ajout à batch
                    print(f"ERROR: batch.add_object failed for {src}: {e}")

        # Après la sortie du contexte batch
        if hasattr(batch, "failed_objects"):
            failed = batch.failed_objects
            if failed:
                print(f"ERROR: {len(failed)} objects failed insertion.")
                for err in failed:
                    print(f"   Failed object: {err}")
    except WeaviateClosedClientError as e:
        print(f"ERROR: weaviate client was closed: {e}, retrying entire batch")
        # Optionnel : relancer en mode direct ou relancer tout le batch
        # pour simplifier, on réessaie une seule fois :
        client = _init_client()
        with client.batch.dynamic() as batch:
            for doc in docs:
                embedding = fetch_embedding_from_ollama(doc.get("text", "")[:8000])
                if not isinstance(embedding, list) or len(embedding) == 0:
                    continue
                try:
                    batch.add_object(
                        collection="Documentation",
                        properties={
                            "text": doc.get("text", ""),
                            "lang": lang,
                            "version": version,
                            "source": doc.get("source")
                        },
                        vector=embedding
                    )
                except WeaviateBaseError as e2:
                    print(f"ERROR RETRY: batch.add_object failed: {e2}")

        if hasattr(batch, "failed_objects"):
            failed = batch.failed_objects
            if failed:
                print(f"ERROR: retry batch failed {len(failed)} objects.")


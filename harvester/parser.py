import os
from pathlib import Path
import re

MAX_CHUNK_SIZE = 20000

def sanitize_text(text: str) -> str:
    text = ''.join(ch for ch in text if ch.isprintable() or ch in "\n\t")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

def extract_docs(repo_path):
    docs = []
    for root, _, files in os.walk(repo_path):
        for f in files:
            if f.endswith((".md", ".markdown", ".txt")):
                path = Path(root) / f
                try:
                    raw = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                text = sanitize_text(raw)
                if len(text) < 50:
                    continue
                if len(text) > MAX_CHUNK_SIZE:
                    for i in range(0, len(text), MAX_CHUNK_SIZE):
                        docs.append({"text": text[i : i + MAX_CHUNK_SIZE], "source": str(path)})
                else:
                    docs.append({"text": text, "source": str(path)})
    return docs

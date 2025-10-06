import os
from pathlib import Path

def extract_docs(repo_path):
    docs = []
    for root, _, files in os.walk(repo_path):
        for f in files:
            if f.endswith((".md", ".markdown", ".txt")):
                path = Path(root) / f
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if len(text.strip()) > 100:
                    docs.append({"text": text, "source": str(path)})
    return docs

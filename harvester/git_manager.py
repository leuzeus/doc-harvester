import os
import subprocess
import yaml
import time
import json

BASE_DIR = "/cache/repos"
CACHE_FILE = "/cache/version_cache.json"
CACHE_TTL = 365 * 24 * 3600  # 1 an

def _load_cache():
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

def list_versions(lang, limit=10):
    with open("/app/harvester/sources.yaml") as f:
        sources = yaml.safe_load(f)
    if lang not in sources:
        raise ValueError(f"Unsupported language: {lang}")
    repo = sources[lang]["repo"]

    cache = _load_cache()
    entry = cache.get(lang)
    now = time.time()
    if entry and (now - entry.get("ts", 0) < CACHE_TTL):
        return entry.get("versions", [])[:limit]

    # Debug : exécution brute
    try:
        res_tags = subprocess.run(
            ["git", "ls-remote", "--refs", "--tags", repo],
            capture_output=True, text=True
        )
    except Exception as e:
        raise RuntimeError(f"git ls-remote tags failed: {e}")
    print("DEBUG tags stdout:", res_tags.stdout)
    print("DEBUG tags stderr:", res_tags.stderr)

    try:
        res_heads = subprocess.run(
            ["git", "ls-remote", "--heads", repo],
            capture_output=True, text=True
        )
    except Exception as e:
        raise RuntimeError(f"git ls-remote heads failed: {e}")
    print("DEBUG heads stdout:", res_heads.stdout)
    print("DEBUG heads stderr:", res_heads.stderr)

    tags_lines = res_tags.stdout.strip().splitlines()
    heads_lines = res_heads.stdout.strip().splitlines()

    versions = []
    for line in tags_lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        if ref.startswith("refs/tags/"):
            tag = ref[len("refs/tags/"):]
            versions.append(tag)

    for line in heads_lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        if ref.startswith("refs/heads/"):
            branch = ref[len("refs/heads/"):]
            versions.append(branch)

    # unique (conserver premier apparition)
    unique = []
    for v in versions:
        if v not in unique:
            unique.append(v)

    # prioriser main / master
    ordered = []
    for b in ["main", "master"]:
        if b in unique:
            ordered.append(b)
    for v in unique:
        if v not in ordered:
            ordered.append(v)

    cache[lang] = {"ts": now, "versions": ordered}
    _save_cache(cache)
    return ordered[:limit]

def clone_repo(lang, version):
    with open("/app/harvester/sources.yaml") as f:
        sources = yaml.safe_load(f)
    if lang not in sources:
        raise ValueError(f"Unsupported language: {lang}")
    repo = sources[lang]["repo"]
    path_in_repo = sources[lang].get("path", "")

    allowed = list_versions(lang, limit=1000)
    if version == "latest":
        version = allowed[0] if allowed else version
    if version not in allowed:
        raise ValueError(f"Version {version} not recognized for {lang}")

    target_dir = os.path.join(BASE_DIR, f"{lang}_{version}")
    if not os.path.exists(target_dir):
        os.makedirs(BASE_DIR, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", "--branch", version, repo, target_dir], check=True)

    return os.path.join(target_dir, path_in_repo)

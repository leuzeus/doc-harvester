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
    except:
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

    # fetch raw refs (tags + branches)
    result_tags = subprocess.run(
        ["git", "ls-remote", "--refs", "--tags", repo],
        capture_output=True, text=True, check=True
    ).stdout.strip().splitlines()
    result_heads = subprocess.run(
        ["git", "ls-remote", "--heads", repo],
        capture_output=True, text=True, check=True
    ).stdout.strip().splitlines()

    versions = []
    # parse tags
    for line in result_tags:
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        if ref.startswith("refs/tags/"):
            tag = ref[len("refs/tags/"):]
            versions.append(tag)
    # parse branches (heads)
    for line in result_heads:
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        if ref.startswith("refs/heads/"):
            branch = ref[len("refs/heads/"):]
            versions.append(branch)

    # unique
    unique = []
    for v in versions:
        if v not in unique:
            unique.append(v)

    # optional: put “main” / “master” first if present
    prioritized = []
    for b in ["main", "master"]:
        if b in unique:
            prioritized.append(b)
    # then append other versions (except those two, already in prioritized)
    for v in unique:
        if v not in prioritized:
            prioritized.append(v)

    # cache
    cache[lang] = {"ts": now, "versions": prioritized}
    _save_cache(cache)

    return prioritized[:limit]

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

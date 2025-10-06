import os
import subprocess
import yaml
import time
import json

BASE_DIR = "/cache/repos"
CACHE_FILE = "/cache/version_cache.json"
CACHE_TTL = int(os.getenv("VERSION_CACHE_TTL", 365 * 24 * 3600))

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
    ignore_branches = sources[lang].get("ignore_branches", False)

    cache = _load_cache()
    entry = cache.get(lang)
    now = time.time()
    if entry and (now - entry.get("ts", 0) < CACHE_TTL):
        return entry.get("versions", [])[:limit]

    # récupérer les tags
    res_tags = subprocess.run(
        ["git", "ls-remote", "--refs", "--tags", repo],
        capture_output=True, text=True
    )
    # debug
    print("DEBUG tags stdout:", res_tags.stdout)
    print("DEBUG tags stderr:", res_tags.stderr)
    tags_lines = res_tags.stdout.strip().splitlines()

    versions = []
    for line in tags_lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        if ref.startswith("refs/tags/"):
            tag = ref[len("refs/tags/"):]
            versions.append(tag)

    # si on n’ignore pas les branches, on les ajoutera
    if not ignore_branches:
        res_heads = subprocess.run(
            ["git", "ls-remote", "--heads", repo],
            capture_output=True, text=True
        )
        print("DEBUG heads stdout:", res_heads.stdout)
        print("DEBUG heads stderr:", res_heads.stderr)
        heads_lines = res_heads.stdout.strip().splitlines()
        for line in heads_lines:
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

    # prioriser main/master si branches non ignorées
    ordered = []
    if not ignore_branches:
        for b in ["main", "master"]:
            if b in unique:
                ordered.append(b)
    # puis le reste (dont tags et branches selon le cas)
    for v in unique:
        if v not in ordered:
            ordered.append(v)

    # inverser l’ordre des versions pour avoir les plus récents en premier (hors main/master)
    base = [v for v in ordered if v in ("main", "master")]
    rest = [v for v in ordered if v not in ("main", "master")]
    rest.reverse()
    final = base + rest

    cache[lang] = {"ts": now, "versions": final}
    _save_cache(cache)
    return final[:limit]

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

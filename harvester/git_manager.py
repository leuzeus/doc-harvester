import os
import subprocess
import yaml
import time
import json
import re
from packaging import version as packaging_version

BASE_DIR = "/cache/repos"
CACHE_FILE = "/cache/version_cache.json"
CACHE_TTL = 365 * 24 * 3600  # 1 an en secondes

SEMVER_TAG_RE = re.compile(r"^(v?\d+\.\d+\.\d+)$")  # ex : "1.2.3" ou "v1.2.3"

def _load_cache():
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
        return data
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
        # cache encore valide
        return entry.get("versions", [])[:limit]

    # sinon, mettre à jour le cache
    # lister les tags
    result = subprocess.run(["git", "ls-remote", "--refs", "--tags", repo],
                             capture_output=True, text=True, check=True)
    lines = result.stdout.strip().splitlines()
    tags = []
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        if ref.startswith("refs/tags/"):
            tag = ref[len("refs/tags/"):]
            # filtrer selon regex semver
            m = SEMVER_TAG_RE.match(tag)
            if m:
                # enlever “v” si présent
                cleaned = tag.lstrip("v")
                tags.append(cleaned)

    # trier selon semver
    try:
        tags = sorted(tags, key=packaging_version.parse, reverse=True)
    except Exception:
        tags = sorted(tags, reverse=True)

    # unique, limiter
    unique = []
    for t in tags:
        if t not in unique:
            unique.append(t)
    top = unique[:limit]

    # détecter branche “main” ou “master”
    branch_main = None
    for br in ["main", "master"]:
        r = subprocess.run(["git", "ls-remote", "--heads", repo, br],
                           capture_output=True, text=True)
        if r.stdout.strip():
            branch_main = br
            break

    versions = []
    if branch_main:
        versions.append(branch_main)
    versions += top

    # enregistrer cache
    cache[lang] = {"ts": now, "versions": versions}
    _save_cache(cache)

    return versions

def clone_repo(lang, version):
    with open("/app/harvester/sources.yaml") as f:
        sources = yaml.safe_load(f)
    if lang not in sources:
        raise ValueError(f"Unsupported language: {lang}")
    repo = sources[lang]["repo"]
    path_in_repo = sources[lang].get("path", "")

    # vérifier version dans la liste autorisée
    allowed = list_versions(lang, limit=50)
    # si version est “latest”, on prend la première de la liste
    if version == "latest":
        version = allowed[0] if allowed else version
    if version not in allowed:
        raise ValueError(f"Version {version} not in allowed list for {lang}")

    target_dir = os.path.join(BASE_DIR, f"{lang}_{version}")
    if not os.path.exists(target_dir):
        os.makedirs(BASE_DIR, exist_ok=True)
        # clonage minimal
        subprocess.run(["git", "clone", "--depth", "1", "--branch", version, repo, target_dir], check=True)

    return os.path.join(target_dir, path_in_repo)

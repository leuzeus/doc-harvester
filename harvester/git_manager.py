import os
import subprocess
import yaml
import tempfile
import shutil

BASE_DIR = "/cache/repos"

def list_versions(lang, limit=10):
    # lit le repo de base dans sources
    with open("/app/harvester/sources.yaml") as f:
        sources = yaml.safe_load(f)
    if lang not in sources:
        raise ValueError(f"Unsupported language: {lang}")
    repo = sources[lang]["repo"]
    # on utilise git ls-remote pour lister tags et branches
    result = subprocess.run(["git", "ls-remote", "--refs", "--tags", repo], capture_output=True, text=True, check=True)
    lines = result.stdout.strip().splitlines()
    tags = []
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        if ref.startswith("refs/tags/"):
            tag = ref[len("refs/tags/"):]
            tags.append(tag)
    # optionnel : trier les tags (selon version semver)
    # garder les plus récents
    tags = sorted(tags, reverse=True)[:limit]
    # ajouter la branche principale (main / master) si elle existe
    # pour ça on peut tester l'existence avec ls-remote
    branch_main = None
    for br in ["main", "master"]:
        r = subprocess.run(["git", "ls-remote", "--heads", repo, br], capture_output=True, text=True)
        if r.stdout.strip():
            branch_main = br
            break
    if branch_main:
        tags.insert(0, branch_main)
    return tags

def clone_repo(lang, version):
    with open("/app/harvester/sources.yaml") as f:
        sources = yaml.safe_load(f)
    if lang not in sources:
        raise ValueError(f"Unsupported language: {lang}")
    repo = sources[lang]["repo"]
    path_in_repo = sources[lang].get("path", "")
    # si version est “latest” ou “main” ou “master”, on utilise la branche principale
    # sinon version = tag
    target_dir = os.path.join(BASE_DIR, f"{lang}_{version}")
    if not os.path.exists(target_dir):
        os.makedirs(BASE_DIR, exist_ok=True)
        # clonage profond minimal
        subprocess.run(["git", "clone", "--depth", "1", "--branch", version, repo, target_dir], check=True)
    return os.path.join(target_dir, path_in_repo)

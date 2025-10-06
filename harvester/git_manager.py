import os, subprocess, yaml

BASE_DIR = "/cache/repos"

def clone_repo(lang, version):
    with open("/app/harvester/sources.yaml") as f:
        sources = yaml.safe_load(f)
    if lang not in sources:
        raise ValueError(f"Unsupported language: {lang}")
    repo = sources[lang]["repo"]
    tag = version if version != "latest" else sources[lang]["versions"][0]
    target_dir = f"{BASE_DIR}/{lang}_{tag}"
    if not os.path.exists(target_dir):
        os.makedirs(BASE_DIR, exist_ok=True)
        subprocess.run(["git", "clone", "--depth=1", "--branch", tag, repo, target_dir], check=True)
    return os.path.join(target_dir, sources[lang]["path"])

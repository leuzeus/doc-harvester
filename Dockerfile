FROM python:3.11-slim
WORKDIR /app

# Installer git (et d'autres dépendances système si nécessaire)
RUN apt-get update && apt-get install -y git curl && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . /app

# Installer des dépendances Python avec version spécifique
RUN pip install \
    fastapi \
    uvicorn \
    "weaviate-client>=4.16.0" \
    pyyaml \
    tqdm \
    requests \
    gitpython

CMD ["python", "main.py"]

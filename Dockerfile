FROM python:3.11-slim
WORKDIR /app

# installer git (et éventuellement les dépendances nécessaires pour git)
RUN apt-get update && apt-get install -y git && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . /app
RUN pip install fastapi uvicorn weaviate-client pyyaml tqdm requests gitpython
CMD ["python", "main.py"]

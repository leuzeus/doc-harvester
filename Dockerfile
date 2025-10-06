FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install fastapi uvicorn weaviate-client pyyaml tqdm requests gitpython
CMD ["python", "main.py"]

# 🧠 Doc Harvester (Weaviate + Ollama)

Service local pour télécharger, parser et indexer automatiquement les documentations versionnées (Go, TinyGo, PHP, React).

## 🚀 Démarrage

```bash
docker compose up -d
```

📥 Ingestion d'une documentation
```bash
curl "http://localhost:8090/fetch?lang=go&version=go1.22.3"
curl "http://localhost:8090/fetch?lang=php&version=php-8.3"
```

🔍 Vérification via Weaviate
```bash
curl -X POST "http://localhost:8080/v1/graphql" -H "Content-Type: application/json" \
-d '{"query":"{ Get { Documentation(where:{operator:Equal, path:[\"lang\"], valueString:\"go\"}) { text sour
```

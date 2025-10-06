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

Pour les modèles à télécharger dans ollama

| Cas d’usage                        | Modèle                   | Taille | Temps / chunk | Commentaire         |
| ---------------------------------- | ------------------------ | ------ | ------------- | ------------------- |
| ⚡ Ingestion rapide, RAG local      | **`nomic-embed-text`**   | 120 MB | ~0.1 s        | ✅ Idéal             |
| 📚 Contexte riche, recherche fine  | `mxbai-embed-large`      | 1.2 GB | ~1 s          | Pour docs complexes |
| 🧪 Expérimental, technique         | `snowflake-arctic-embed` | 1 GB   | ~0.8 s        | Bon mix             |

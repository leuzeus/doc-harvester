# 🧠 Doc Harvester (Weaviate + Ollama)

Service local (usage personnel) pour télécharger, parser et indexer automatiquement les documentations versionnées (Go, TinyGo, PHP, React).

## 🚀 Démarrage

```bash
docker compose up -d
```

📥 Ingestion d'une documentation
```bash
curl "http://your_ip:8090/fetch?lang=go&version=1.22.3"
curl "http://your_ip:8090/fetch?lang=php&version=8.3"
```

🔍 Vérification via Weaviate
```bash
curl -X POST "http://your_ip_2:8080/v1/graphql" -H "Content-Type: application/json" \
-d '{"query":"{ Get { Documentation(where:{operator:Equal, path:[\"lang\"], valueString:\"go\"}) { text sour
```

Pour le choix du modèles à télécharger dans ollama

| Cas d’usage                        | Modèle                   | Taille | Temps / chunk | Commentaire         |
| ---------------------------------- | ------------------------ | ------ | ------------- | ------------------- |
| ⚡ Ingestion rapide, RAG local      | **`nomic-embed-text`**   | 120 MB | ~0.1 s        | ✅ Idéal             |
| 📚 Contexte riche, recherche fine  | `mxbai-embed-large`      | 1.2 GB | ~1 s          | Pour docs complexes |
| 🧪 Expérimental, technique         | `snowflake-arctic-embed` | 1 GB   | ~0.8 s        | Bon mix             |

💡 Pourquoi les ports ne sont pas exposés

Les ports ne sont pas exposés, car les services tournent dans un réseau Docker isolé.
Seuls les autres conteneurs du même réseau y ont accès, ce qui évite d’ouvrir inutilement des ports vers l’extérieur et garde la stack plus simple.

Depuis ce réseau, un service peut streamer ou consommer les autres sans problème.
N’hésitez pas à adapter cette approche selon votre infrastructure ou vos besoins d’accès.

## TODO
[] Fournir d'autres sources de documentation
[] Ajouter une base de donnée
[] Page de connexion + admin pour la gestion des sources
[] Permettre une sélection des versions de document à précharger
[] Ajouter un seveur MCP

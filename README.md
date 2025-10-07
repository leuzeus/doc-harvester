# Doc Harvester

## Overview
Doc Harvester downloads, parses, and indexes documentation sets so they can be queried through a vector database. It now ships with an admin interface to manage the source configurations without touching YAML files manually.

## Getting Started
- **Docker workflow:** `docker compose up -d`
- **Manual ingestion:**
  - `curl "http://your_ip:8090/fetch?lang=go&version=1.22.3"`
  - `curl "http://your_ip:8090/fetch?lang=php&version=8.3"`

## Admin Interface
1. `pip install -r requirements.txt`
2. `uvicorn main:app --reload --port 8000`

The admin dashboard is available at `http://localhost:8000/admin` and provides full CRUD capabilities for the source catalog. Use the **Export Sources YAML** action (`POST /admin/export-sources-yaml`) to write the current configuration to `harvester/sources.yaml` and receive the YAML payload in the response.

## API Endpoints
- `GET /versions?lang=<lang>&limit=<limit>` lists available documentation versions.
- `GET /fetch?lang=<lang>&version=<version>` clones, parses, and indexes a documentation release.

## Notes
- Default embeddings are handled by the Weaviate vector store; adapt them for your environment as needed.
- Recommended Ollama embedding models:
  - `nomic-embed-text` for fast local ingestion.
  - `mxbai-embed-large` when rich semantic context is required.
  - `snowflake-arctic-embed` for experimental setups.

## Roadmap
- Additional documentation sources
- Database-backed source catalog (done)
- Authentication and admin hardening
- Pre-selectable documentation versions
- MCP server integration

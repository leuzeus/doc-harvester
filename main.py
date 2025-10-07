"""Main FastAPI application entry point."""

# Standard library imports
from pathlib import Path

# Third-party imports
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

# Local application imports
from admin import create_admin
from harvester.git_manager import clone_repo, list_versions
from harvester.parser import extract_docs
from harvester.vectorizer import push_to_weaviate
from models import get_session, init_db
from utils.yaml_export import export_sources_to_yaml


# --------------------------------------------------------------------------------------
# Application setup
# --------------------------------------------------------------------------------------
app = FastAPI(title="Doc Harvester")

# Initialize the database schema and admin interface at import time to avoid race issues.
init_db()
create_admin(app)

# Shared path constants
BASE_PATH = Path(__file__).resolve().parent
HARVESTER_SOURCES_PATH = BASE_PATH / "harvester" / "sources.yaml"


# --------------------------------------------------------------------------------------
# Harvester operations endpoints
# --------------------------------------------------------------------------------------
@app.get("/versions")
def versions(lang: str = Query(...), limit: int = Query(10)):
    """Return available documentation versions for the requested language."""

    try:
        vers = list_versions(lang, limit)
        return {"lang": lang, "versions": vers}
    except Exception as exc:  # pragma: no cover - defensive programming
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/fetch")
def fetch_docs(lang: str = Query(...), version: str = Query("latest")):
    """Clone, parse, and push documentation to the vector store."""

    try:
        repo_path = clone_repo(lang, version)
        docs = extract_docs(repo_path)
        push_to_weaviate(docs, lang, version)
        return {"status": "ok", "count": len(docs), "lang": lang, "version": version}
    except ValueError as value_error:
        raise HTTPException(status_code=400, detail=str(value_error)) from value_error
    except Exception as exc:  # pragma: no cover - defensive programming
        message = f"Internal error: {exc}"
        raise HTTPException(status_code=500, detail=message) from exc


# --------------------------------------------------------------------------------------
# Admin utilities
# --------------------------------------------------------------------------------------
@app.post("/admin/export-sources-yaml", response_class=PlainTextResponse)
def export_sources_yaml(session: Session = Depends(get_session)) -> PlainTextResponse:
    """Persist sources to ``harvester/sources.yaml`` and return the YAML payload."""

    yaml_text = export_sources_to_yaml(session=session, target_path=HARVESTER_SOURCES_PATH)
    return PlainTextResponse(content=yaml_text, media_type="text/yaml")


if __name__ == "__main__":  # pragma: no cover
    uvicorn.run(app, host="0.0.0.0", port=8090)

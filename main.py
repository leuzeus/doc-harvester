from fastapi import FastAPI, Query, HTTPException
from harvester.git_manager import list_versions, clone_repo
from harvester.parser import extract_docs
from harvester.vectorizer import push_to_weaviate
import uvicorn

app = FastAPI(title="Doc Harvester")

@app.get("/versions")
def versions(lang: str = Query(...), limit: int = Query(10)):
    try:
        vers = list_versions(lang, limit)
        return {"lang": lang, "versions": vers}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/fetch")
def fetch_docs(lang: str = Query(...), version: str = Query("latest")):
    try:
        repo_path = clone_repo(lang, version)
        docs = extract_docs(repo_path)
        push_to_weaviate(docs, lang, version)
        return {"status": "ok", "count": len(docs), "lang": lang, "version": version}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error: " + str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)

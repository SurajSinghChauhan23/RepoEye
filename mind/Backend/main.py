from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.ingest_routes import router as ingest_router
from app.api.query_routes import router as query_router
from app.api.repository_routes import router as repository_router

app = FastAPI(title="RepoMind API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create runtime directories
Path("artifacts").mkdir(parents=True, exist_ok=True)
Path("cloned_files").mkdir(parents=True, exist_ok=True)
Path("cache").mkdir(parents=True, exist_ok=True)
Path("db").mkdir(parents=True, exist_ok=True)

# Mount static artifacts folder
app.mount("/artifacts", StaticFiles(directory="artifacts"), name="artifacts")

# Include routers
app.include_router(ingest_router, prefix="/ingest", tags=["Ingestion"])
app.include_router(query_router, prefix="/query", tags=["Query"])
app.include_router(repository_router, prefix="/api/repository", tags=["Repository"])
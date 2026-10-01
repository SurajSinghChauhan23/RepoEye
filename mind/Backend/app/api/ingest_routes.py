from fastapi import APIRouter, BackgroundTasks, HTTPException
from pathlib import Path
import uuid
import pickle

from ..core.state import state
from ..schemas.ingest import (
    IngestRequest,
    IngestStartResponse,
    IngestStatusResponse,
    FileTreeNode
)
from Ingestion.ingestion import run_ingestion, clone_repo, get_repo_hash

router = APIRouter()


def build_tree(path: Path) -> dict:
    if path.is_file():
        return {
            "name": path.name,
            "path": str(path),
            "type": "file",
            "children": []
        }

    return {
        "name": path.name,
        "path": str(path),
        "type": "folder",
        "children": [
            build_tree(p)
            for p in path.iterdir()
            if not p.name.startswith(".")
        ]
    }


async def ingestion_task(repo_id: str, git_url: str):
    try:
        await run_ingestion(git_url)

        # Load repo specific graph
        repo_hash = get_repo_hash(git_url)
        graph_path = Path("graphs") / f"{repo_hash}.pkl"

        with open(graph_path, "rb") as f:
            state.graph = pickle.load(f)

        state.repos[repo_id]["status"] = "completed"

    except Exception as e:
        state.repos[repo_id]["status"] = "failed"
        state.repos[repo_id]["error"] = str(e)


@router.post("/repo", response_model=IngestStartResponse)
async def start_ingestion(payload: IngestRequest, background_tasks: BackgroundTasks):
    repo_id = str(uuid.uuid4())
    repo_name = payload.git_url.split("/")[-1].replace(".git", "")
    repo_path = Path("cloned_files") / repo_name
    
    # Clone the repository first to get the file tree
    try:
        clone_path = await clone_repo(payload.git_url)
        # Use the returned path from clone_repo
        repo_path = clone_path
    except Exception as e:
        raise HTTPException(500, f"Failed to clone repository: {str(e)}")
    
    # Build tree after cloning
    tree = None
    if repo_path.exists():
        try:
            tree = build_tree(repo_path)
        except Exception as e:
            raise HTTPException(500, f"Failed to build file tree: {str(e)}")
    else:
        raise HTTPException(500, "Repository directory not found after cloning")

    state.repos[repo_id] = {
        "status": "processing",
        "tree": tree
    }
    
    # Run the full ingestion in the background
    background_tasks.add_task(ingestion_task, repo_id, payload.git_url)
    
    return {
        "repo_id": repo_id,
        "file_tree": tree
    }


@router.get("/status/{repo_id}")
def get_status(repo_id: str):
    repo = state.repos.get(repo_id)
    if not repo:
        raise HTTPException(404, "Repo not found")

    return {
        "status": repo["status"]
    }


@router.get("/health")
def health_check():
    return {"status": "ok"}
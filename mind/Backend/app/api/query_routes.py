from fastapi import APIRouter, HTTPException
from pathlib import Path
import pickle
import hashlib

from ..schemas.query import QueryRequest, QueryResponse, ChatHistoryResponse
from ..core.state import state
from retrieval.main import run

router = APIRouter()


def get_repo_hash(git_url: str) -> str:
    return hashlib.md5(git_url.encode()).hexdigest()[:8]


def load_graph_for_repo(git_url: str):
    repo_hash = get_repo_hash(git_url)
    graph_path = Path(f"graphs/{repo_hash}.pkl")

    if not graph_path.exists():
        raise HTTPException(400, "Graph not found. Run ingestion first.")

    with open(graph_path, "rb") as f:
        state.graph = pickle.load(f)


@router.post("/", response_model=QueryResponse)
def query(payload: QueryRequest):

    # Always load graph of the repo being queried
    load_graph_for_repo(payload.repo_url)

    response = run(
        user_query=payload.query,
        frontend_section=payload.intent,
        graph=state.graph,
        hash=get_repo_hash(payload.repo_url)
    )

    # Save to chat history
    state.add_to_history(payload.query, payload.intent, response)

    return response


@router.get("/history", response_model=ChatHistoryResponse)
def get_chat_history():
    return ChatHistoryResponse(history=state.chat_history)


@router.delete("/history")
def clear_chat_history():
    state.chat_history = []
    state.save_history()
    return {"message": "Chat history cleared"}
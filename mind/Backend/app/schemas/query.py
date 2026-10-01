from pydantic import BaseModel
from typing import Dict, Any, List


class QueryRequest(BaseModel):
    repo_url: str
    query: str
    intent: str


class QueryResponse(BaseModel):
    intent: str
    confidence: float
    responses: Dict[str, Any]
    hash:str


class ChatHistoryEntry(BaseModel):
    timestamp: str
    query: str
    intent: str
    response: Dict[str, Any]


class ChatHistoryResponse(BaseModel):
    history: List[ChatHistoryEntry]
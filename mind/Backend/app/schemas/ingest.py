from pydantic import BaseModel
from typing import List, Optional


class FileTreeNode(BaseModel):
    name: str
    path: str
    type: str
    children: List["FileTreeNode"] = []


class IngestRequest(BaseModel):
    git_url: str


class IngestStartResponse(BaseModel):
    repo_id: str
    file_tree: Optional[FileTreeNode]


class IngestStatusResponse(BaseModel):
    status: str

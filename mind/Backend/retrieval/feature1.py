from typing import List, Tuple
import networkx as nx

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from collections import deque


# =========================================================
# Hybrid traversal (BFS + shallow helper DFS)
# =========================================================
def extract_flow_subgraph(
    graph: nx.DiGraph,
    entry_nodes: List[str],
    max_depth: int = 3,
    helper_depth: int = 1
) -> List[str]:

    visited = set()
    ordered = []
    queue = deque()

    for entry in entry_nodes:
        if graph.has_node(entry):
            queue.append((entry, 0))

    while queue:
        node, depth = queue.popleft()

        if node in visited or depth > max_depth:
            continue

        visited.add(node)
        ordered.append(node)

        for succ in graph.successors(node):
            queue.append((succ, depth + 1))

        if depth <= helper_depth:
            for pred in graph.predecessors(node):
                if pred not in visited:
                    queue.append((pred, depth + 1))

    return ordered


# =========================================================
# Chunk retrieval
# =========================================================
def fetch_chunks_by_id(
    chunk_ids: List[str],
    graph: nx.DiGraph,
    repo_hash: str
) -> List[Document]:

    if not chunk_ids:
        return []

    embedding_model = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    vectorstore = Chroma(
        persist_directory=f"RepoMind/db/chroma_db/{repo_hash}",
        embedding_function=embedding_model
    )
    print("FLOW NODES:", chunk_ids)

    valid_ids = [
        cid for cid in chunk_ids
        if graph.nodes.get(cid, {}).get("type") != "parameter"
    ]
    print("VALID IDS:", valid_ids)
    if not valid_ids:
        return []

    results = vectorstore.get(
        where={"hash": {"$in": valid_ids}}
    )

    docs = []
    for content, metadata in zip(
        results.get("documents", []),
        results.get("metadatas", [])
    ):
        docs.append(
            Document(
                page_content=content,
                metadata=metadata
            )
        )

    print("DOCS FOUND:", len(results.get("documents", [])))    

    return docs


# =========================================================
# Explanation LLM
# =========================================================
def send_to_llm(
    docs: List[Document],
    query: str
) -> str:

    llm = ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview",
        temperature=0
    )

    context = "\n\n".join(
        doc.page_content for doc in docs
    )

    prompt = f"""
You are an expert full-stack software architect.

Using ONLY the context below, explain the COMPLETE
end-to-end execution flow (frontend → backend → response).

Context:
----------------
{context}
----------------

Rules:
- No assumptions
- No hallucination
- Explain execution order clearly

Question:
{query}
"""

    response = llm.invoke(
        [HumanMessage(content=prompt)]
    )

    return response.content[0]["text"]


# =========================================================
# Public API
# =========================================================
def run_feature1(
    graph: nx.DiGraph,
    entry_nodes: List[str],
    query: str,
    repo_hash: str
) -> Tuple[str, List[str]]:

    flow_nodes = extract_flow_subgraph(
        graph,
        entry_nodes
    )

    docs = fetch_chunks_by_id(
        flow_nodes,
        graph,
        repo_hash
    )

    if not docs:
        return "", flow_nodes

    explanation = send_to_llm(
        docs,
        query
    )

    return explanation, flow_nodes
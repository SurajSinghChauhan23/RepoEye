import json
from typing import List, Dict
from functools import lru_cache
from dotenv import load_dotenv

import networkx as nx
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


# =========================================================
# Shared / cached resources
# =========================================================

@lru_cache(maxsize=1)
def get_embedding_model():
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )


@lru_cache(maxsize=10)
def get_vectorstore(repo_hash: str):
    return Chroma(
        persist_directory=f"RepoMind/db/chroma_db/{repo_hash}",
        embedding_function=get_embedding_model()
    )


@lru_cache(maxsize=1)
def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview",
        temperature=0
    )


# =========================================================
# Semantic entry-point discovery
# =========================================================
def semantic_entry_discovery(
    concept_entities: List[str],
    explanation_query: str,
    graph: nx.DiGraph,
    repo_hash: str,
    top_k: int = 3
) -> List[str]:

    vectorstore = get_vectorstore(repo_hash)
    print("RETRIEVAL PATH:", f"RepoMind/db/chroma_db/{repo_hash}")
    print("VECTORSTORE COUNT:", vectorstore._collection.count())

    candidate_docs: List[Document] = vectorstore.similarity_search(
        explanation_query,
        k=10
    )

    candidate_nodes = []
    for doc in candidate_docs:
        chunk_hash = doc.metadata.get("hash")
        if chunk_hash and graph.has_node(chunk_hash):
            candidate_nodes.append(chunk_hash)
        print("VECTOR RESULT HASH:", doc.metadata.get("hash"))
        print("GRAPH HAS NODE:", graph.has_node(doc.metadata.get("hash")))   
    print("Candidate nodes from vector search:", candidate_nodes)
    if not candidate_nodes:
        return []

    scored = []
    for node in set(candidate_nodes):
        out_degree = graph.out_degree(node)
        in_degree = graph.in_degree(node)
        reachable = len(nx.descendants(graph, node))

        score = (out_degree * 2) + reachable - in_degree
        scored.append((node, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    return [n for n, _ in scored[:top_k]]


# =========================================================
# User query normalization
# =========================================================
def normalize_user_query(
    user_query: str,
    frontend_section: str
) -> Dict:

    llm = get_llm()

    system_prompt = f"""
You are an intent normalization engine for a code intelligence system.

Rules:
- DO NOT answer the question
- DO NOT add or remove meaning
- DO NOT assume missing context
- ONLY classify intent and rewrite the SAME question

Allowed intents:
- explanation
- impact_analysis
- call_flow

Frontend-selected intent: {frontend_section}

Entity rules:
- Mentioned functions/classes → symbol_entities
- High-level concepts → concept_entities
- Do NOT invent entities

Return ONLY valid JSON:

{{
  "primary_intent": "<intent>",
  "secondary_intents": [],
  "queries": {{
    "<intent>": "<rephrased question>"
  }},
  "symbol_entities": [],
  "concept_entities": [],
  "needs_semantic_discovery": true,
  "confidence": 0.0
}}
"""

    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]
    )

    try:
        parsed = json.loads(response.content[0]["text"])

        if "queries" not in parsed:
            parsed["queries"] = {
                parsed["primary_intent"]: user_query
            }

        return parsed

    except Exception:
        return {
            "primary_intent": frontend_section,
            "secondary_intents": [],
            "queries": {
                frontend_section: user_query
            },
            "symbol_entities": [],
            "concept_entities": [],
            "needs_semantic_discovery": False,
            "confidence": 0.5
        }
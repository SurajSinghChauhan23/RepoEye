from typing import Dict, Any
import networkx as nx
from pathlib import Path

from .retrival import (
    normalize_user_query,
    semantic_entry_discovery
)

# -------- Feature 1 (Explanation) --------
from .feature1 import run_feature1

# -------- Feature 2 (Impact Analysis) --------
from .feature2 import run_feature2

# -------- Feature 3 (Visualization / Structure) --------
from .feature3 import run_feature3


# =========================================================
# Feature 1 Router
# =========================================================
def run_explanation_feature(refined: Dict, graph: nx.DiGraph, repo_hash: str):
    entry_nodes = semantic_entry_discovery(
        refined["concept_entities"],
        refined["queries"]["explanation"],
        graph,
        repo_hash
    )

    explanation, flow_nodes = run_feature1(
        graph=graph,
        entry_nodes=entry_nodes,
        query=refined["queries"]["explanation"],
        repo_hash=repo_hash
    )

    structure = run_feature3(
        graph=graph,
        nodes=flow_nodes,
        output_dir="artifacts",
        filename="feature1_structure"
    )

    svg_path = structure.get("svg_path")
    image_url = f"/artifacts/{Path(svg_path).name}" if svg_path else None

    return {
        "text": explanation,
        "structure": structure,
        "image_url": image_url
    }


# =========================================================
# Feature 2 Router
# =========================================================
def run_impact_feature(refined: Dict, graph: nx.DiGraph, repo_hash: str):
    entry_nodes = semantic_entry_discovery(
        refined["concept_entities"],
        refined["queries"]["impact_analysis"],
        graph,
        repo_hash
    )[:1]

    explanation, impact_data, involved_nodes = run_feature2(
        graph=graph,
        changed_nodes=entry_nodes,
        query=refined["queries"]["impact_analysis"],
        repo_hash=repo_hash
    )

    structure = run_feature3(
        graph=graph,
        nodes=involved_nodes,
        output_dir="artifacts",
        filename="feature2_structure"
    )

    svg_path = structure.get("svg_path")
    image_url = f"/artifacts/{Path(svg_path).name}" if svg_path else None

    return {
        "text": explanation,
        "impact_data": impact_data,
        "structure": structure,
        "image_url": image_url
    }


# =========================================================
# Feature 3 Router (Standalone)
# =========================================================
def run_structure_feature(refined: Dict, graph: nx.DiGraph, repo_hash: str):
    entry_nodes = semantic_entry_discovery(
        refined["concept_entities"],
        refined["queries"]["call_flow"],
        graph,
        repo_hash
    )

    structure = run_feature3(
        graph=graph,
        nodes=entry_nodes,
        output_dir="artifacts",
        filename="feature3_structure"
    )

    svg_path = structure.get("svg_path")
    image_url = f"/artifacts/{Path(svg_path).name}" if svg_path else None

    return {
        "structure": structure,
        "image_url": image_url
    }


# =========================================================
# 🚀 MAIN RETRIEVAL ENTRYPOINT
# =========================================================
def run(
    user_query: str,
    frontend_section: str,
    graph: nx.DiGraph,
    hash: str
) -> Dict[str, Any]:

    refined = normalize_user_query(
        user_query,
        frontend_section
    )

    responses = {}
    primary = refined["primary_intent"]

    if primary == "explanation":
        responses["explanation"] = run_explanation_feature(
            refined,
            graph,
            hash
        )

    elif primary == "impact_analysis":
        responses["impact_analysis"] = run_impact_feature(
            refined,
            graph,
            hash
        )

    elif primary == "call_flow":
        responses["system_structure"] = run_structure_feature(
            refined,
            graph,
            hash
        )

    return {
        "intent": refined["primary_intent"],
        "confidence": refined.get("confidence", 0.0),
        "responses": responses,
        "hash": hash
    }
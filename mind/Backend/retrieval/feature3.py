import os
from typing import List, Dict
from pathlib import Path
import networkx as nx
from graphviz import Digraph


# =========================================================
# Feature 3 — Structure Graph Builder (Graphviz Version)
# =========================================================

def run_feature3(
    graph: nx.DiGraph,
    nodes: List[str],
    output_dir: str = "artifacts",
    filename: str = "feature_structure"
) -> Dict:

    """
    Generates a STRUCTURAL GRAPH using Graphviz.

    Improvements over Mermaid:
    - hierarchical layout
    - clustering by file
    - colored node types
    - better spacing
    """

    if not nodes:
        return {}

    os.makedirs(output_dir, exist_ok=True)

    svg_path = os.path.join(output_dir, f"{filename}.svg")

    # -------------------------------------------------
    # Graphviz graph
    # -------------------------------------------------

    dot = Digraph(
        name="RepoMindStructure",
        format="svg",
        engine="dot"
    )

    dot.attr(rankdir="LR")
    dot.attr(
        "graph",
        fontsize="12",
        fontname="Helvetica",
        nodesep="0.6",
        ranksep="1.2",
        splines="spline"
    )

    dot.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fontname="Helvetica",
        fontsize="10"
    )

    dot.attr(
        "edge",
        color="#555555"
    )

    # -------------------------------------------------
    # Group nodes by file (clusters)
    # -------------------------------------------------

    file_clusters = {}

    for node in nodes:

        if not graph.has_node(node):
            continue

        data = graph.nodes[node]

        file_path = data.get("file", "unknown")
        file_name = Path(file_path).name

        file_clusters.setdefault(file_name, []).append(node)

    # -------------------------------------------------
    # Render clusters
    # -------------------------------------------------

    for file_name, file_nodes in file_clusters.items():

        with dot.subgraph(name=f"cluster_{file_name}") as c:

            c.attr(label=file_name, style="rounded")

            for node in file_nodes:

                data = graph.nodes[node]

                func = node.split("::")[-1]
                params = data.get("params", [])
                ntype = data.get("type", "unknown")

                params_str = ", ".join(params) if params else "—"

                label = f"{func}\n({params_str})\n[{ntype}]"

                # -------------------------------------------------
                # Color nodes by type
                # -------------------------------------------------

                if ntype == "async_function":
                    color = "#E3F2FD"

                elif ntype == "function":
                    color = "#E8F5E9"

                elif ntype == "class":
                    color = "#FFF3E0"

                else:
                    color = "#ECEFF1"

                c.node(
                    node,
                    label=label,
                    fillcolor=color
                )

    # -------------------------------------------------
    # Add edges
    # -------------------------------------------------

    for src in nodes:

        for dst in graph.successors(src):

            if src in nodes and dst in nodes:
                dot.edge(src, dst)

    # -------------------------------------------------
    # Render graph
    # -------------------------------------------------

    dot.render(
        filename=filename,
        directory=output_dir,
        cleanup=True
    )

    return {
        "svg_path": svg_path,
        "total_nodes": len(nodes)
    }
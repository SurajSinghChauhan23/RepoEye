import networkx as nx
import pickle
from pathlib import Path


def create_graph(all_chunks, all_relations, repo_hash):

    G = nx.DiGraph()

    def chunk_id(chunk):
        """
        Use chunk hash as stable node ID.
        Falls back to file::name if hash not present.
        """
        return chunk.get("hash") or f"{chunk['file_path']}::{chunk['name']}"

    # Map (file_path, name) → node
    file_name_to_node = {}

    # Map name → nodes
    name_to_nodes = {}

    # Map hash → node
    hash_to_node = {}

    for chunk in all_chunks:

        cid = chunk_id(chunk)

        hash_to_node[chunk.get("hash")] = cid

        key = (str(chunk["file_path"]), chunk["name"])
        file_name_to_node[key] = cid

        name_to_nodes.setdefault(chunk["name"], []).append(cid)

    def resolve_node(name, file_path=None, chunk_hash=None):
        """
        Resolve nodes in priority order:
        1️⃣ hash
        2️⃣ file + name
        3️⃣ name fallback
        """

        if chunk_hash:
            node = hash_to_node.get(chunk_hash)
            if node:
                return node

        if file_path:
            node = file_name_to_node.get((file_path, name))
            if node:
                return node

        nodes = name_to_nodes.get(name)
        return nodes[0] if nodes else None

    # Add nodes
    for chunk in all_chunks:

        node_id = chunk_id(chunk)

        G.add_node(
            node_id,
            type=chunk["type"],
            file=str(chunk["file_path"]),
            language=chunk.get("language", "unknown"),
            params=chunk.get("params", []),
            decorators=chunk.get("decorators", []),
            hash=chunk.get("hash")  # store hash in metadata
        )

    # Add edges
    for rel in all_relations:

        src = resolve_node(rel["from"])
        dst = resolve_node(rel["to"])

        if not src or not dst:
            continue

        G.add_edge(
            src,
            dst,
            type=rel["type"],
            language=rel.get("language", "unknown"),
            confidence=rel.get("confidence", "unknown"),
            route=rel.get("route"),
            http_method=rel.get("http_method"),
            backend_method=rel.get("backend_method"),
            api_type=rel.get("api_type"),
        )

    # create graphs directory
    graph_dir = Path("graphs")
    graph_dir.mkdir(exist_ok=True)

    graph_path = graph_dir / f"{repo_hash}.pkl"

    with open(graph_path, "wb") as f:
        pickle.dump(G, f)

    return G
from tree_sitter import Language, Parser
import tree_sitter_java as tsjava
import tree_sitter_javascript as tsjs
from pathlib import Path
from typing import List
import hashlib

def compute_chunk_hash(code):
    return hashlib.sha1(code.encode()).hexdigest()

JAVA_LANGUAGE = Language(tsjava.language())
def java_ast_parser(file_path: Path):
    chunks = []
    seen_nodes = set()

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()

    parser = Parser(JAVA_LANGUAGE)
    tree = parser.parse(source.encode("utf-8"))
    ANNOTATION_USAGE_NODES = {
        "annotation",
        "marker_annotation",
        "annotation_argument_list",
    }
    def extract_direct_identifier(node):
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode("utf-8")
        return None
    def get_chunk_type(node):
        if node.type == "annotation_type_declaration":
            return "annotation"
        if node.type == "class_declaration":
            return "class"
        if node.type == "interface_declaration":
            return "interface"
        if node.type == "enum_declaration":
            return "enum"
        if node.type == "constructor_declaration":
            return "constructor"
        if node.type == "method_declaration":
            if node.parent and node.parent.type == "class_body":
                return "method"
            return "function" 
        return None
    def walk(node):
        if id(node) in seen_nodes:
            return
        seen_nodes.add(id(node))
        if node.type in ANNOTATION_USAGE_NODES:
            return
        chunk_type = get_chunk_type(node)
        if chunk_type:
            start = node.start_point[0] + 1
            end = node.end_point[0] + 1
            name = extract_direct_identifier(node) or file_path.stem
            
            # Extract decorators/annotations for bridge inference
            decorators = []
            for child in node.children:
                if child.type in ("annotation", "marker_annotation"):
                    decorators.append(child.text.decode("utf-8"))
            
            code = "\n".join(source.splitlines()[start - 1:end])
            chunks.append({
                "name": name,
                "file_path": file_path,
                "type": chunk_type,
                "code": code,
                "start_line": start,
                "end_line": end,
                "decorators": decorators,
                "hash": compute_chunk_hash(code)  
            })
        for child in node.children:
            walk(child)
    walk(tree.root_node)
    if not chunks:
        chunks.append({
            "name": file_path.stem,
            "file_path": file_path,
            "type": "module",
            "code": source,
            "start_line": 1,
            "end_line": len(source.splitlines()),
            "hash": compute_chunk_hash(source)
        })
    return chunks,tree

from tree_sitter import Language, Parser
import tree_sitter_javascript as tsjs
from pathlib import Path
import hashlib
import re

JS_LANGUAGE = Language(tsjs.language())

API_PATTERNS = [
    "fetch(",
    "axios.",
    "axios(",
    ".get(",
    ".post(",
    ".put(",
    ".delete(",
    "/api",
]

# Regex version for fast scan
API_REGEX = re.compile(
    r"fetch\(|axios\.|axios\(|\.get\(|\.post\(|\.put\(|\.delete\(|/api"
)

def compute_chunk_hash(code):
    return hashlib.sha1(code.encode()).hexdigest()


def js_ast_parser(file_path: Path):

    chunks = []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()

    # ------------------------------------------------
    # HYBRID STEP 1: FAST REGEX CHECK
    # Skip AST parsing completely if no API usage
    # ------------------------------------------------
    if not API_REGEX.search(source):
        return chunks, None

    # ------------------------------------------------
    # HYBRID STEP 2: Build AST only if necessary
    # ------------------------------------------------
    parser = Parser(JS_LANGUAGE)
    tree = parser.parse(source.encode("utf-8"))

    lines = source.splitlines()

    def extract_identifier(node):
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode("utf-8")
        return None

    def get_chunk_type(node):

        if node.type == "function_declaration":
            return "function"

        if node.type == "class_declaration":
            return "class"

        if node.type == "method_definition":
            return "method"

        if node.type == "arrow_function":
            if node.parent and node.parent.type == "variable_declarator":
                return "arrow_function"

        return None

    def walk(node):

        # ------------------------------------------------
        # Skip JSX-heavy React nodes (huge AST savings)
        # ------------------------------------------------
        if node.type.startswith("jsx"):
            return

        chunk_type = get_chunk_type(node)

        if chunk_type:

            start = node.start_point[0] + 1
            end = node.end_point[0] + 1

            code = "\n".join(lines[start - 1:end])

            # Only keep chunks related to API logic
            if not any(p in code for p in API_PATTERNS):
                return

            name = extract_identifier(node) or file_path.stem

            chunks.append({
                "name": name,
                "file_path": file_path,
                "type": "api_logic",
                "code": code,
                "start_line": start,
                "end_line": end,
                "decorators": [],
                "hash": compute_chunk_hash(code)
            })

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    # ------------------------------------------------
    # Fallback if no specific chunk detected
    # ------------------------------------------------
    if not chunks:
        chunks.append({
            "name": file_path.stem,
            "file_path": file_path,
            "type": "module",
            "code": source,
            "start_line": 1,
            "end_line": len(lines),
            "decorators": [],
            "hash": compute_chunk_hash(source)
        })

    return chunks, tree
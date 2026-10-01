import ast
import hashlib
from pathlib import Path
from typing import List, Dict

def compute_chunk_hash(code: str):
    return hashlib.sha1(code.encode()).hexdigest()

def ast_parser(file_path: Path):
    chunks = []

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()

        lines = file_content.splitlines()   # NEW: compute once
        tree = ast.parse(file_content)

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return chunks, None

    # -----------------------------------------------------
    # Keep parent assignment (unchanged logic)
    # -----------------------------------------------------
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent

    # -----------------------------------------------------
    # Chunk type classification (unchanged)
    # -----------------------------------------------------
    def get_chunk_type(node):
        if isinstance(node, ast.ClassDef):
            return "class"

        if isinstance(node, ast.AsyncFunctionDef):
            if isinstance(getattr(node, "parent", None), ast.ClassDef):
                return "async_method"
            return "async_function"

        if isinstance(node, ast.FunctionDef):
            if isinstance(getattr(node, "parent", None), ast.ClassDef):

                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        if decorator.id == "staticmethod":
                            return "static_method"
                        if decorator.id == "classmethod":
                            return "class_method"

                return "method"

            return "function"

        return "unknown"

    # -----------------------------------------------------
    # Extract chunks
    # -----------------------------------------------------
    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):

            start = node.lineno
            end = node.end_lineno

            # FAST extraction instead of ast.get_source_segment()
            code = "\n".join(lines[start - 1:end])

            decorators = []
            if hasattr(node, "decorator_list"):
                for decorator in node.decorator_list:

                    deco_str = (
                        ast.unparse(decorator)
                        if hasattr(ast, "unparse")
                        else str(decorator)
                    )

                    decorators.append(deco_str)

            chunks.append({
                "name": node.name,
                "file_path": file_path,
                "type": get_chunk_type(node),
                "code": code,
                "start_line": start,
                "end_line": end,
                "decorators": decorators,
                "hash": compute_chunk_hash(code)
            })

    # -----------------------------------------------------
    # fallback if no chunks
    # -----------------------------------------------------
    if not chunks:

        chunks.append({
            "name": file_path.stem,
            "file_path": file_path,
            "type": "module",
            "code": file_content,
            "start_line": 1,
            "end_line": len(lines),
            "hash": compute_chunk_hash(file_content)
        })

    return chunks, tree
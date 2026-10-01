from tree_sitter import Language, Parser
import tree_sitter_javascript as tsjs
from pathlib import Path
from typing import List


def extract_js_calls(chunks, tree, file_name):
    relations = []
    
    # Create a mapping of chunk names to chunks for easy access
    chunk_map = {}
    for chunk in chunks:
        chunk_map[chunk["name"]] = chunk

    # NEW: Build line → chunk map
    line_map = {}
    for chunk in chunks:
        for line in range(chunk["start_line"], chunk["end_line"] + 1):
            line_map[line] = chunk["name"]

    def extract_params(node):
        params = []
        for child in node.children:
            if child.type == "formal_parameters":
                for p in child.children:
                    if p.type == "identifier":
                        params.append(p.text.decode("utf-8"))
                    elif p.type == "rest_pattern":
                        for g in p.children:
                            if g.type == "identifier":
                                params.append("..." + g.text.decode("utf-8"))
        return params

    def walk(node):

        start_line = node.start_point[0] + 1 if node.start_point else None

        if node.type == "import_statement":
            relations.append({
                "from": file_name,
                "to": node.text.decode("utf-8"),
                "type": "import",
                "language": "javascript",
                "confidence": "explicit"
            })

        if node.type == "class_declaration":

            class_name = None
            parent_class = None

            for child in node.children:
                if child.type == "identifier":
                    class_name = child.text.decode("utf-8")

                if child.type == "class_heritage":
                    for g in child.children:
                        if g.type == "identifier":
                            parent_class = g.text.decode("utf-8")

            if class_name and parent_class:
                relations.append({
                    "from": class_name,
                    "to": parent_class,
                    "type": "inherits",
                    "language": "javascript",
                    "confidence": "explicit"
                })

        # NEW: constant-time caller lookup
        caller = None
        if start_line:
            caller = line_map.get(start_line)

        if caller:

            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        relations.append({
                            "from": caller,
                            "to": child.text.decode("utf-8"),
                            "type": "call",
                            "language": "javascript",
                            "confidence": "syntactic"
                        })

            if node.type == "new_expression":
                for child in node.children:
                    if child.type == "identifier":
                        relations.append({
                            "from": caller,
                            "to": child.text.decode("utf-8"),
                            "type": "instantiates",
                            "language": "javascript",
                            "confidence": "explicit"
                        })

        if node.type in (
            "function_declaration",
            "method_definition",
            "arrow_function",
        ):

            name = None

            for child in node.children:
                if child.type == "identifier":
                    name = child.text.decode("utf-8")

            params = extract_params(node)

            if name and name in chunk_map:
                if "params" not in chunk_map[name]:
                    chunk_map[name]["params"] = []
                chunk_map[name]["params"].extend(params)

            if name:
                for p in params:
                    relations.append({
                        "from": name,
                        "to": p,
                        "type": "parameter",
                        "language": "javascript",
                        "confidence": "explicit"
                    })

        if node.type == "decorator":
            relations.append({
                "from": file_name,
                "to": node.text.decode("utf-8"),
                "type": "decorated_by",
                "language": "javascript",
                "confidence": "explicit"
            })

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    return relations
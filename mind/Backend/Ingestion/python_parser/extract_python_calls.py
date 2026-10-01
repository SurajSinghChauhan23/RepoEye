import ast
from pathlib import Path

def extract_python_calls(chunks, tree, file_name):
    relations = []
    
    # Create a mapping of chunk names to chunks for easy access
    chunk_map = {}
    for chunk in chunks:
        chunk_map[chunk["name"]] = chunk

    # NEW: Build line → chunk map for O(1) lookup
    line_map = {}
    for chunk in chunks:
        for line in range(chunk["start_line"], chunk["end_line"] + 1):
            line_map[line] = chunk["name"]

    def extract_params(func_node):
        params = []

        for arg in func_node.args.args:
            params.append(arg.arg)

        if func_node.args.vararg:
            params.append(f"*{func_node.args.vararg.arg}")

        for arg in func_node.args.kwonlyargs:
            params.append(arg.arg)

        if func_node.args.kwarg:
            params.append(f"**{func_node.args.kwarg.arg}")

        return params

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                relations.append({
                    "from": file_name,
                    "to": alias.name,
                    "type": "import",
                    "language": "python",
                    "line": node.lineno,
                    "confidence": "explicit"
                })

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                relations.append({
                    "from": file_name,
                    "to": f"{module}.{alias.name}",
                    "type": "import",
                    "language": "python",
                    "line": node.lineno,
                    "confidence": "explicit"
                })

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name):
                    parent = base.id
                elif isinstance(base, ast.Attribute):
                    parent = base.attr
                else:
                    parent = ast.dump(base)

                relations.append({
                    "from": node.name,
                    "to": parent,
                    "type": "inherits",
                    "language": "python",
                    "confidence": "syntactic"
                })

            for body_item in node.body:
                if isinstance(body_item, ast.FunctionDef) and body_item.name == "__init__":
                    params = extract_params(body_item)
                    for p in params:
                        relations.append({
                            "from": node.name,
                            "to": p,
                            "type": "parameter",
                            "language": "python",
                            "confidence": "explicit"
                        })

    for node in ast.walk(tree):

        if not hasattr(node, "lineno"):
            continue

        # NEW: constant-time lookup instead of scanning all chunks
        caller = line_map.get(node.lineno)

        if not caller:
            continue

        if isinstance(node, ast.Call):

            if isinstance(node.func, ast.Name):
                callee = node.func.id
            elif isinstance(node.func, ast.Attribute):
                callee = node.func.attr
            else:
                callee = ast.dump(node.func)

            relations.append({
                "from": caller,
                "to": callee,
                "type": "call",
                "language": "python",
                "line": node.lineno,
                "confidence": "syntactic"
            })

            if isinstance(node.func, ast.Name):
                relations.append({
                    "from": caller,
                    "to": node.func.id,
                    "type": "instantiates",
                    "language": "python",
                    "line": node.lineno,
                    "confidence": "heuristic"
                })

        if isinstance(node, ast.Return):
            relations.append({
                "from": caller,
                "to": "return",
                "type": "returns",
                "language": "python",
                "line": node.lineno,
                "confidence": "explicit"
            })

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = extract_params(node)
            
            if node.name in chunk_map:
                if "params" not in chunk_map[node.name]:
                    chunk_map[node.name]["params"] = []
                chunk_map[node.name]["params"].extend(params)
            
            for p in params:
                relations.append({
                    "from": node.name,
                    "to": p,
                    "type": "parameter",
                    "language": "python",
                    "confidence": "explicit"
                })

            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    deco = decorator.id
                elif isinstance(decorator, ast.Attribute):
                    deco = decorator.attr
                else:
                    deco = ast.dump(decorator)

                relations.append({
                    "from": node.name,
                    "to": deco,
                    "type": "decorated_by",
                    "language": "python",
                    "confidence": "explicit"
                })

    return relations
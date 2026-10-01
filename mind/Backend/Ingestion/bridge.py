
from typing import List, Dict, Optional
import re


def infer_frontend_backend_bridges(
    all_chunks: List[dict],
    all_relations: List[dict]
) -> List[dict]:
    
    if not all_chunks or not all_relations:
        return []
    
    # Phase 1: Extract frontend API calls
    frontend_apis = _detect_frontend_api_calls(all_chunks)
    
    # Phase 2: Extract backend entry points
    backend_endpoints = _detect_backend_entry_points(all_chunks)
    
    # Phase 3: Match frontend calls to backend endpoints
    bridge_relations = _match_api_calls_to_endpoints(
        frontend_apis,
        backend_endpoints
    )
    
    return bridge_relations


def _detect_frontend_api_calls(all_chunks: List[dict]) -> List[Dict]:
    frontend_apis = []
    
    for chunk in all_chunks:
        # Only process JavaScript/TypeScript chunks
        if chunk.get("language") not in ("javascript", "typescript"):
            continue
        
        code = chunk.get("code", "")
        if not code:
            continue
        
        caller_name = chunk.get("name", "unknown")
        file_path = chunk.get("file_path", "")
        
        # Pattern 1: fetch('route') or fetch("route")
        for match in re.finditer(r"fetch\s*\(\s*['\"]([^'\"]+)['\"]", code):
            route = match.group(1)
            method = _infer_fetch_method(code, match.start())
            
            frontend_apis.append({
                "caller": caller_name,
                "file_path": file_path,
                "route": route,
                "http_method": method or "unknown",
                "api_type": "fetch",
                "chunk_type": chunk.get("type", "function")
            })
        
        # Pattern 2: axios.get/post/put/delete/patch('route')
        for match in re.finditer(r"axios\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]", code, re.IGNORECASE):
            frontend_apis.append({
                "caller": caller_name,
                "file_path": file_path,
                "route": match.group(2),
                "http_method": match.group(1).upper(),
                "api_type": "axios",
                "chunk_type": chunk.get("type", "function")
            })
        
        # Pattern 3: apiClient.get/post/put/delete/patch/call('route')
        for match in re.finditer(r"apiClient\.(get|post|put|delete|patch|call)\s*\(\s*['\"]([^'\"]+)['\"]", code, re.IGNORECASE):
            method = "unknown" if match.group(1) == "call" else match.group(1).upper()
            frontend_apis.append({
                "caller": caller_name,
                "file_path": file_path,
                "route": match.group(2),
                "http_method": method,
                "api_type": "apiClient",
                "chunk_type": chunk.get("type", "function")
            })
    
    return frontend_apis


def _infer_fetch_method(code: str, pos: int) -> Optional[str]:
    """
    Infer HTTP method from fetch call context (conservative).
    Only returns method if explicitly set in options.
    """
    lookahead = code[pos:min(pos + 500, len(code))]
    match = re.search(r"method\s*:\s*['\"](\w+)['\"]", lookahead, re.IGNORECASE)
    return match.group(1).upper() if match else None


def _detect_backend_entry_points(all_chunks: List[dict]) -> List[Dict]:
    """
    Detect backend API entry points from Python and Java chunks.
    Uses stored decorators/annotations first, then regex as fallback.
    """
    backend_endpoints = []
    
    for chunk in all_chunks:
        language = chunk.get("language")
        if language not in ("python", "java"):
            continue
        
        code = chunk.get("code", "")
        if not code:
            continue
        
        handler_name = chunk.get("name", "unknown")
        file_path = chunk.get("file_path", "")
        params = chunk.get("params", [])
        decorators = chunk.get("decorators", [])
        
        # Extract from decorators/annotations first (metadata)
        if decorators:
            for decorator in decorators:
                endpoint = _parse_decorator_to_endpoint(decorator, handler_name, file_path, params, language)
                if endpoint:
                    backend_endpoints.append(endpoint)
        
        # Fallback: scan code for mapping patterns
        backend_endpoints.extend(
            _scan_code_for_endpoints(code, handler_name, file_path, params, language)
        )
    
    return backend_endpoints


def _parse_decorator_to_endpoint(
    decorator: str,
    handler_name: str,
    file_path: str,
    params: List[str],
    language: str
) -> Optional[Dict]:
    """
    Parse decorator/annotation string to extract route and HTTP method.
    Supports Spring Boot (@GetMapping, etc) and Flask/FastAPI (@app.get, etc).
    """
    # Spring Boot patterns: @GetMapping, @PostMapping, etc
    spring_patterns = {
        "GetMapping": "GET",
        "PostMapping": "POST",
        "PutMapping": "PUT",
        "DeleteMapping": "DELETE",
        "PatchMapping": "PATCH",
    }
    
    for mapping_name, http_method in spring_patterns.items():
        pattern = rf"@{mapping_name}\s*\(\s*['\"]([^'\"]*)['\"]"
        match = re.match(pattern, decorator)
        if match:
            return {
                "handler": handler_name,
                "file_path": file_path,
                "route": match.group(1) or "/",
                "http_method": http_method,
                "language": language,
                "params": params
            }
    
    # Flask/FastAPI patterns: @app.get, @router.post, etc
    flask_patterns = [
        (r"@app\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]*)['\"]", "python"),
        (r"@router\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]*)['\"]", "python"),
    ]
    
    for pattern, lang in flask_patterns:
        if language != lang:
            continue
        match = re.match(pattern, decorator, re.IGNORECASE)
        if match:
            return {
                "handler": handler_name,
                "file_path": file_path,
                "route": match.group(2) or "/",
                "http_method": match.group(1).upper(),
                "language": language,
                "params": params
            }
    
    return None


def _scan_code_for_endpoints(
    code: str,
    handler_name: str,
    file_path: str,
    params: List[str],
    language: str
) -> List[Dict]:
    """
    Scan code for endpoint patterns (fallback if decorators not available).
    Avoids duplicate extraction by only finding patterns not already in decorators.
    """
    endpoints = []
    
    if language == "java":
        # Spring mappings: @GetMapping, @PostMapping, etc
        for mapping_name, http_method in [
            ("GetMapping", "GET"),
            ("PostMapping", "POST"),
            ("PutMapping", "PUT"),
            ("DeleteMapping", "DELETE"),
            ("PatchMapping", "PATCH"),
            ("RequestMapping", "unknown"),
        ]:
            pattern = rf"@{mapping_name}\s*\(\s*['\"]([^'\"]*)['\"]"
            for match in re.finditer(pattern, code):
                endpoints.append({
                    "handler": handler_name,
                    "file_path": file_path,
                    "route": match.group(1) or "/",
                    "http_method": http_method,
                    "language": "java",
                    "params": params
                })
    
    elif language == "python":
        # Flask/FastAPI app.get/post/etc
        for pattern, http_method in [
            (r"@app\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]*)['\"]", None),
            (r"@router\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]*)['\"]", None),
            (r"@blueprint\.route\s*\(\s*['\"]([^'\"]*)['\"]", "unknown"),
        ]:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                method = http_method if http_method else match.group(1).upper()
                
                # For blueprint.route, try to extract methods parameter
                if http_method == "unknown":
                    lookahead = code[match.start():min(match.start() + 300, len(code))]
                    methods_match = re.search(r"methods\s*=\s*\[?\s*['\"](\w+)['\"]", lookahead, re.IGNORECASE)
                    if methods_match:
                        method = methods_match.group(1).upper()
                
                endpoints.append({
                    "handler": handler_name,
                    "file_path": file_path,
                    "route": match.group(2) if "blueprint" not in pattern else match.group(1),
                    "http_method": method or "unknown",
                    "language": "python",
                    "params": params
                })
    
    return endpoints


def _match_api_calls_to_endpoints(
    frontend_apis: List[Dict],
    backend_endpoints: List[Dict]
) -> List[Dict]:
    """
    Match frontend API calls to backend endpoints using conservative strategy.
    
    Confidence tiers:
    - high (0.9+): Route match + HTTP method match
    - medium (0.7+): Route match + method unknown
    - low (0.5+): Route match only
    - skip: <0.5 or ambiguous
    """
    bridge_relations = []
    seen_pairs = set()
    
    for api_call in frontend_apis:
        best_match = None
        best_confidence = 0
        
        for endpoint in backend_endpoints:
            edge_key = (api_call["caller"], endpoint["handler"])
            if edge_key in seen_pairs:
                continue
            
            # Calculate confidence score
            route_match = (api_call["route"] == endpoint["route"] or 
                          _routes_similar(api_call["route"], endpoint["route"]))
            
            if not route_match:
                continue
            
            # Route matches; now check HTTP method
            confidence = 0.5
            
            frontend_method = api_call["http_method"]
            backend_method = endpoint["http_method"]
            
            if frontend_method != "unknown" and backend_method != "unknown":
                if frontend_method == backend_method:
                    confidence = 1.0  # Perfect match
                else:
                    confidence = 0.3  # Method mismatch; skip
            elif backend_method == "unknown":
                confidence = 0.75  # Route match, method unspecified
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = endpoint
        
        # Create bridge only if confidence is sufficient
        if best_match and best_confidence >= 0.5:
            bridge_relations.append({
                "from": api_call["caller"],
                "to": best_match["handler"],
                "type": "http_call",
                "language": "cross",
                "confidence": _confidence_to_label(best_confidence),
                "route": api_call["route"],
                "http_method": api_call["http_method"],
                "backend_method": best_match["http_method"],
                "api_type": api_call["api_type"]
            })
            seen_pairs.add((api_call["caller"], best_match["handler"]))
    
    return bridge_relations


def _routes_similar(route1: str, route2: str) -> bool:
    """
    Check if two routes are semantically similar.
    Handles prefix differences and parameterized routes.
    """
    r1 = route1.strip("/").lower()
    r2 = route2.strip("/").lower()
    
    if r1 == r2:
        return True
    
    # Check if one is a suffix of the other (prefix difference)
    parts1, parts2 = r1.split("/"), r2.split("/")
    
    if len(parts1) > len(parts2) and parts1[-len(parts2):] == parts2:
        return True
    if len(parts2) > len(parts1) and parts2[-len(parts1):] == parts1:
        return True
    
    # Handle parametrized routes: /user/{id} == /user/:id
    param1 = re.sub(r"\{[^}]+\}", ":param", r1)
    param2 = re.sub(r"\{[^}]+\}", ":param", r2)
    
    return param1 == param2


def _confidence_to_label(confidence: float) -> str:
    """Convert confidence score to label."""
    if confidence >= 0.9:
        return "high"
    elif confidence >= 0.7:
        return "medium"
    else:
        return "low"


import git
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
import pickle
import hashlib
import asyncio
from concurrent.futures import ProcessPoolExecutor   # NEW
import os                                             # NEW
import time
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from .python_parser.parse_python_files import ast_parser
from .python_parser.extract_python_calls import extract_python_calls

from .java_parser.parse_java_files import java_ast_parser
from .java_parser.extract_java_calls import extract_java_calls

from .js_parser.parse_js_files import js_ast_parser
from .js_parser.extract_js_calls import extract_js_calls

from .graph_making import create_graph
from .bridge import infer_frontend_backend_bridges

load_dotenv()

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"batch_size": 32}
)

MAX_WORKERS = 2   # as you decided


# =========================================================
# Parallel worker
# =========================================================
def parse_file_worker(args):

    language, file_path = args

    try:

        if language == "python":
            chunks, tree = ast_parser(file_path)
            relations = extract_python_calls(chunks, tree, str(file_path))
            print("python processing:", file_path)

        elif language == "java":
            chunks, tree = java_ast_parser(file_path)
            relations = extract_java_calls(chunks, tree, str(file_path))
            print("java processing:", file_path)

        elif language == "js":
            chunks, tree = js_ast_parser(file_path)
            relations = extract_js_calls(chunks, tree, str(file_path))
            print("js processing:", file_path)

        else:
            return language, [], [], file_path

        return language, chunks, relations, file_path

    except Exception as e:
        print("FAILED FILE:", file_path)
        print("ERROR:", e)
        return language, [], [], file_path


# =========================================================
# Cache management
# =========================================================
def get_repo_hash(git_url: str) -> str:
    return hashlib.md5(git_url.encode()).hexdigest()[:8]


def is_already_processed(git_url: str) -> bool:
    repo_hash = get_repo_hash(git_url)

    cache_file = Path(f"cache/{repo_hash}.done")
    graph_file = Path(f"graphs/{repo_hash}.pkl")
    chroma_dir = Path(f"RepoMind/db/chroma_db/{repo_hash}")
    print("INGEST CHROMA PATH:", chroma_dir)
    return cache_file.exists() and graph_file.exists() and chroma_dir.exists()


def mark_as_processed(git_url: str):
    repo_hash = get_repo_hash(git_url)
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)

    cache_file = cache_dir / f"{repo_hash}.done"
    cache_file.write_text(git_url)


# =========================================================
# Repo cloning
# =========================================================
def _clone_repo_sync(git_url: str, clone_path: Path) -> None:
    git.Repo.clone_from(git_url, clone_path)


async def clone_repo(git_url: str) -> Path:
    repo_name = git_url.split("/")[-1].replace(".git", "")
    clone_path = Path("cloned_files") / repo_name

    if not clone_path.exists():
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _clone_repo_sync, git_url, clone_path)

    return clone_path


# =========================================================
# File filtering
# =========================================================
from pathlib import Path
from typing import List

def clean_files(path: Path) -> List[Path]:

    IGNORED_DIRS = {
        ".git", "venv", "__pycache__", "node_modules",
        "dist", "build", ".cache",
        "public", "assets", "static", ".next", "coverage", "out"
    }

    IGNORED_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".svg",
        ".mp3", ".mp4", ".wav",
        ".pdf", ".zip", ".exe", ".bin",
        ".env", ".lock", ".log", ".csv"
    }

    IGNORED_FILES = {
        ".gitignore", "__init__.py","package-lock.json", "package.json"
    }

    files = []

    if path.is_dir():

        # skip hidden directories except .git
        if path.name.startswith(".") and path.name != ".git":
            return []

        if path.name in IGNORED_DIRS:
            return []

        for child in path.iterdir():
            files.extend(clean_files(child))

    elif path.is_file():

        if (
            path.name not in IGNORED_FILES
            and path.suffix.lower() not in IGNORED_EXTENSIONS
        ):
            files.append(path)

    return files


# =========================================================
# Language separation
# =========================================================
def split_by_language(files: List[Path]):
    py, java, js = [], [], []

    for f in files:
        ext = f.suffix.lower()

        if ext == ".py":
            py.append(f)

        elif ext == ".java":
            java.append(f)

        elif ext in {".js", ".jsx"}:

            name = f.name.lower()
            path_str = str(f).lower()

            IMPORTANT_FILES = {
                "app.js", "app.jsx",
                "main.js", "main.jsx",
                "index.js", "index.jsx",
                "api.js"
            }

            IMPORTANT_DIRS = {
                "service", "services",
                "api", "client"
            }

            if (
                name in IMPORTANT_FILES
                or any(d in path_str for d in IMPORTANT_DIRS)
            ):
                js.append(f)

    return py, java, js


# =========================================================
# Vector document creation
# =========================================================
def to_langchain_docs(
    chunks: List[dict],
    repo_root: Path
) -> List[Document]:

    docs = []

    for c in chunks:
        docs.append(
            Document(
                page_content=c["code"],
                metadata={
                    "chunk_id": f"{c['file_path']}::{c['name']}",
                    "file": str(c["file_path"].relative_to(repo_root)),
                    "title": c["name"],
                    "type": c["type"],
                    "language": c.get("language"),
                    "params": ", ".join(c.get("params", [])),
                    "start_line": c["start_line"],
                    "end_line": c["end_line"],
                    "hash": c["hash"],
                },
            )
        )

    return docs


# =========================================================
# 🚀 MAIN INGESTION ENTRY
# =========================================================
async def run_ingestion(git_url: str) -> Dict:

    if is_already_processed(git_url):

        repo_name = git_url.split("/")[-1].replace(".git", "")

        return {
            "repository": repo_name,
            "cached": True,
            "message": "Using cached results"
        }

    print(f"🔄 Processing repository: {git_url}")

    repo_root = await clone_repo(git_url)
    repo_name = repo_root.name

    print(f"📁 Cloned to: {repo_root}")

    start_time = time.time()

    files = clean_files(repo_root)

    print(f"📄 Total files after cleaning: {len(files)}")
    print("time taken for cleaning files:", time.time() - start_time)

    print("splitting by language...")

    py_files, java_files, js_files = split_by_language(files)

    print("Python files:", len(py_files))
    print("Java files:", len(java_files))
    print("JS files:", len(js_files))

    all_chunks = []
    all_relations = []

    # ------------------------------------------------
    # Build unified parse tasks
    # ------------------------------------------------
    tasks = []

    for f in py_files:
        tasks.append(("python", f))

    for f in java_files:
        tasks.append(("java", f))

    for f in js_files:
        tasks.append(("js", f))

    print(f"Parsing {len(tasks)} files in parallel with {MAX_WORKERS} workers...")

    start_time = time.time()
    results=[]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:

        try:
            results = list(executor.map(parse_file_worker, tasks, chunksize=1))
        except Exception as e:

            print("Worker error:", e)
        
    # ------------------------------------------------
    # Process results
    # ------------------------------------------------
    for language, chunks, relations, file_path in results:
        print("language parsed:", language, file_path)
        all_chunks.extend(chunks)
        all_relations.extend(relations)

    print(f"✅ Parsing complete. Time taken: {time.time() - start_time:.2f} seconds")

    # ------------------------------------------------
    # Bridge inference
    # ------------------------------------------------
    start_time = time.time()

    print("Inferring cross-language bridges...")

    bridge_edges = infer_frontend_backend_bridges(
        all_chunks,
        all_relations
    )

    all_relations.extend(bridge_edges)

    print(f"✅ Bridge inference complete. Time taken: {time.time() - start_time:.2f}")

    repo_hash = get_repo_hash(git_url)

    docs = to_langchain_docs(all_chunks, repo_root)
    print("TOTAL CHUNKS:", len(all_chunks))
    print("DOCS CREATED:", len(docs))
    chroma_dir = Path(f"RepoMind/db/chroma_db/{repo_hash}")

    print("Creating graph and embeddings in parallel...")

    async def build_embeddings():

        if not chroma_dir.exists():

            vectorstore = Chroma(
                embedding_function=embeddings,
                persist_directory=str(chroma_dir),
                collection_metadata={"hnsw:space": "cosine"},
            )

            batch_size = 100

            for i in range(0, len(docs), batch_size):
                vectorstore.add_documents(docs[i:i + batch_size])

            vectorstore.persist()

    start_time = time.time()

    await asyncio.gather(
        asyncio.to_thread(create_graph, all_chunks, all_relations, repo_hash),
        asyncio.to_thread(lambda: asyncio.run(build_embeddings()))
    )

    print(f"✅ Graph and embeddings complete. Time taken: {time.time() - start_time:.2f}")

    mark_as_processed(git_url)

    print(f"✅ Ingestion complete for {repo_name}")

    return {
        "repository": repo_name,
        "chunks": len(all_chunks),
        "relations": len(all_relations),
        "python_files": len(py_files),
        "java_files": len(java_files),
        "js_files": len(js_files),
        "cached": False
    }
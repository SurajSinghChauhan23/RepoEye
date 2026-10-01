from fastapi import APIRouter, HTTPException, Query
from pathlib import Path

router = APIRouter()


@router.get("/file")
def get_file_content(repo_id: str = Query(...), path: str = Query(...)):
    """
    Returns the content of a file from the cloned repository.
    """
    try:
        file_path = Path(path)
        
        if not file_path.exists():
            raise HTTPException(404, f"File not found: {path}")
        
        if not file_path.is_file():
            raise HTTPException(400, f"Path is not a file: {path}")
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Handle binary files
            raise HTTPException(400, "Cannot display binary file content")
        
        return {
            "path": str(file_path),
            "content": content,
            "name": file_path.name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error reading file: {str(e)}")
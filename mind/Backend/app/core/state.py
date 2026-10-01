import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class AppState:
    def __init__(self):
        self.graph = None
        self.repos = {}  # repo_id → {status, tree}
        self.chat_history: List[Dict[str, Any]] = []
        self._load_history()

    def _load_history(self):
        history_file = Path("db/chat_history.json")
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    self.chat_history = json.load(f)
            except Exception:
                self.chat_history = []

    def save_history(self):
        history_file = Path("db/chat_history.json")
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, "w") as f:
            json.dump(self.chat_history, f, indent=2, default=str)

    def add_to_history(self, query: str, intent: str, response: Dict[str, Any]):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "intent": intent,
            "response": response
        }
        self.chat_history.append(entry)
        self.save_history()


state = AppState()

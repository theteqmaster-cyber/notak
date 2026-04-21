import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any

class MboardElement:
    """Base class for all elements on the Mboard canvas."""
    def __init__(self, id=None, type="generic", x=0, y=0, width=100, height=100, style=None):
        self.id = id or str(uuid.uuid4())
        self.type = type
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.style = style or {}

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "style": self.style
        }

    @staticmethod
    def from_dict(data):
        return MboardElement(**data)

class MboardData:
    """Represents the full data structure of a single board."""
    def __init__(self, title="Untitled Board", elements: List[MboardElement] = None):
        self.title = title
        self.version = "1.0"
        self.created_at = datetime.now().isoformat()
        self.last_modified = datetime.now().isoformat()
        self.elements = elements or []
        self.viewport = {"center_x": 0, "center_y": 0, "zoom": 1.0}

    def to_dict(self):
        return {
            "title": self.title,
            "version": self.version,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "viewport": self.viewport,
            "elements": [e.to_dict() if isinstance(e, MboardElement) else e for e in self.elements]
        }

    @staticmethod
    def from_dict(data):
        m = MboardData(data.get("title", "Untitled Board"))
        m.version = data.get("version", "1.0")
        m.created_at = data.get("created_at")
        m.last_modified = data.get("last_modified")
        m.viewport = data.get("viewport", m.viewport)
        m.elements = data.get("elements", [])
        return m

class CanvasManager:
    """Handles saving and loading Mboard files."""
    def __init__(self):
        self.base_dir = os.path.expanduser("~/StudyVault/Mboards")
        os.makedirs(self.base_dir, exist_ok=True)

    def get_all_boards(self):
        boards = []
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".mboard"):
                path = os.path.join(self.base_dir, filename)
                boards.append({
                    "name": filename.replace(".mboard", ""),
                    "path": path,
                    "mtime": os.path.getmtime(path)
                })
        return sorted(boards, key=lambda x: x['mtime'], reverse=True)

    def save_board(self, board_data: MboardData, filename: str):
        if not filename.endswith(".mboard"):
            filename += ".mboard"
        
        path = os.path.join(self.base_dir, filename)
        board_data.last_modified = datetime.now().isoformat()
        
        with open(path, "w") as f:
            json.dump(board_data.to_dict(), f, indent=4)
        return path

    def load_board(self, path: str) -> MboardData:
        with open(path, "r") as f:
            data = json.load(f)
        return MboardData.from_dict(data)

    def create_board(self, title: str) -> str:
        data = MboardData(title)
        # Ensure unique filename
        filename = title
        counter = 1
        while os.path.exists(os.path.join(self.base_dir, f"{filename}.mboard")):
            filename = f"{title}_{counter}"
            counter += 1
            
        return self.save_board(data, filename)

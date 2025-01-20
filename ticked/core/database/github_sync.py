import base64
import json
import requests
import shutil
from pathlib import Path
from typing import Optional, Tuple

class GithubSync:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.api_base = "https://api.github.com"
        self.token = None

    def set_token(self, token: str) -> None:
        self.token = token

    def create_or_update_gist(self, gist_id: Optional[str] = None) -> Tuple[str, str]:
        if not self.token:
            raise ValueError("GitHub token not set")
            
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Read database file as binary
        with open(self.db_path, 'rb') as f:
            content = f.read()
            
        # Create base64 content for JSON
        content_b64 = base64.b64encode(content).decode('utf-8')

        if gist_id:
            url = f"{self.api_base}/gists/{gist_id}"
            method = requests.patch
        else:
            url = f"{self.api_base}/gists"
            method = requests.post

        data = {
            "description": "Ticked Database Sync",
            "public": False,
            "files": {
                "tick.db": {
                    "content": content_b64
                }
            }
        }

        response = method(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        return result["id"], result["files"]["tick.db"]["raw_url"]

    def download_and_replace_db(self, gist_id: str) -> bool:
        if not self.token:
            raise ValueError("GitHub token not set")
            
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Get the gist first
        response = requests.get(f"{self.api_base}/gists/{gist_id}", headers=headers)
        response.raise_for_status()
        
        # Get the content from the gist response directly
        content_b64 = response.json()["files"]["tick.db"]["content"]
        
        # Decode the base64 content
        db_content = base64.b64decode(content_b64)

        # Create backup
        backup_path = self.db_path + ".backup"
        shutil.copy2(self.db_path, backup_path)

        try:
            with open(self.db_path, 'wb') as f:
                f.write(db_content)
            return True
        except Exception as e:
            # Restore from backup if something goes wrong
            shutil.copy2(backup_path, self.db_path)
            raise e
        finally:
            Path(backup_path).unlink(missing_ok=True)
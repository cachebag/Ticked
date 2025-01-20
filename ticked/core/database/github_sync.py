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
        
    def set_token(self, token: str) -> None:
        self.token = token
        
    def create_or_update_gist(self, gist_id: Optional[str] = None) -> Tuple[str, str]:
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        with open(self.db_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode()
            
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
                    "content": content
                }
            }
        }
        
        response = method(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["id"], result["files"]["tick.db"]["raw_url"]
        
    def download_and_replace_db(self, gist_id: str) -> bool:
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(f"{self.api_base}/gists/{gist_id}", headers=headers)
        response.raise_for_status()
        raw_url = response.json()["files"]["tick.db"]["raw_url"]
        
        db_content = requests.get(raw_url).content
        backup_path = self.db_path + ".backup"
        
        shutil.copy2(self.db_path, backup_path)
        try:
            with open(self.db_path, 'wb') as f:
                f.write(base64.b64decode(db_content))
            return True
        except:
            shutil.copy2(backup_path, self.db_path)
            return False
        finally:
            Path(backup_path).unlink(missing_ok=True)
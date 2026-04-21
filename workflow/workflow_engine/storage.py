"""
Workflow Storage
Handles persistence of workflow definitions
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class WorkflowStorage:
    """Handles workflow storage and retrieval"""
    
    def __init__(self, storage_path: str = "./data/workflows"):
        self.storage_path = Path(storage_path)
        self._ensure_storage_dir()
        
    def _ensure_storage_dir(self):
        """Ensure storage directory exists"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    def _get_workflow_path(self, workflow_id: str) -> Path:
        """Get the file path for a workflow"""
        return self.storage_path / f"{workflow_id}.json"
        
    def save_workflow(self, workflow_id: str, workflow_data: dict) -> bool:
        """Save a workflow to storage"""
        try:
            path = self._get_workflow_path(workflow_id)
            
            # Add metadata
            workflow_data["id"] = workflow_id
            if "updated_at" not in workflow_data:
                workflow_data["updated_at"] = datetime.now().isoformat()
                
            with open(path, "w", encoding="utf-8") as f:
                json.dump(workflow_data, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to save workflow {workflow_id}: {e}")
            
    def load_workflow(self, workflow_id: str) -> Optional[dict]:
        """Load a workflow from storage"""
        try:
            path = self._get_workflow_path(workflow_id)
            
            if not path.exists():
                return None
                
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
                
        except Exception as e:
            raise StorageError(f"Failed to load workflow {workflow_id}: {e}")
            
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow from storage"""
        try:
            path = self._get_workflow_path(workflow_id)
            
            if path.exists():
                path.unlink()
                
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to delete workflow {workflow_id}: {e}")
            
    def list_workflows(self) -> List[dict]:
        """List all workflows in storage"""
        workflows = []
        
        for path in self.storage_path.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    workflows.append({
                        "id": data.get("id", path.stem),
                        "name": data.get("name", "Unnamed"),
                        "description": data.get("description"),
                        "version": data.get("version", "1.0.0"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at")
                    })
            except Exception:
                continue
                
        return sorted(workflows, key=lambda x: x.get("updated_at", ""), reverse=True)
        
    def get_workflow_metadata(self, workflow_id: str) -> Optional[dict]:
        """Get metadata for a workflow without loading full content"""
        try:
            path = self._get_workflow_path(workflow_id)
            
            if not path.exists():
                return None
                
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "id": data.get("id", workflow_id),
                    "name": data.get("name", "Unnamed"),
                    "description": data.get("description"),
                    "version": data.get("version", "1.0.0"),
                    "author": data.get("author"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "trigger": data.get("trigger", {}).get("type")
                }
                
        except Exception:
            return None
            
    def export_workflow(self, workflow_id: str, export_path: str) -> bool:
        """Export a workflow to a specific path"""
        try:
            workflow = self.load_workflow(workflow_id)
            if not workflow:
                return False
                
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(workflow, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to export workflow {workflow_id}: {e}")
            
    def import_workflow(self, import_path: str, new_id: str = None) -> str:
        """Import a workflow from a file"""
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                workflow = json.load(f)
                
            # Generate new ID if not specified
            if new_id is None:
                import uuid
                new_id = workflow.get("id") or f"wf_{uuid.uuid4().hex[:8]}"
                
            workflow["id"] = new_id
            workflow["imported_at"] = datetime.now().isoformat()
            
            self.save_workflow(new_id, workflow)
            return new_id
            
        except Exception as e:
            raise StorageError(f"Failed to import workflow: {e}")
            
    def duplicate_workflow(self, workflow_id: str, new_name: str = None) -> str:
        """Duplicate an existing workflow"""
        try:
            workflow = self.load_workflow(workflow_id)
            if not workflow:
                raise StorageError(f"Workflow {workflow_id} not found")
                
            import uuid
            new_id = f"wf_{uuid.uuid4().hex[:8]}"
            
            workflow["id"] = new_id
            workflow["name"] = new_name or f"{workflow.get('name', 'Workflow')} (Copy)"
            workflow["created_at"] = datetime.now().isoformat()
            workflow["updated_at"] = None
            
            self.save_workflow(new_id, workflow)
            return new_id
            
        except Exception as e:
            raise StorageError(f"Failed to duplicate workflow {workflow_id}: {e}")
            
    def search_workflows(self, query: str) -> List[dict]:
        """Search workflows by name or description"""
        query = query.lower()
        results = []
        
        for wf in self.list_workflows():
            name = wf.get("name", "").lower()
            desc = wf.get("description", "").lower()
            
            if query in name or query in desc:
                results.append(wf)
                
        return results
        
    def get_workflow_count(self) -> int:
        """Get total number of workflows"""
        return len(list(self.storage_path.glob("*.json")))
        
    def clear_all(self) -> int:
        """Delete all workflows (use with caution)"""
        count = 0
        for path in self.storage_path.glob("*.json"):
            path.unlink()
            count += 1
        return count
        
    def backup(self, backup_path: str) -> bool:
        """Create a backup of all workflows"""
        try:
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            for path in self.storage_path.glob("*.json"):
                shutil.copy2(path, backup_dir / path.name)
                
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to backup workflows: {e}")
            
    def restore(self, backup_path: str) -> int:
        """Restore workflows from a backup"""
        count = 0
        backup_dir = Path(backup_path)
        
        if not backup_dir.exists():
            raise StorageError(f"Backup path does not exist: {backup_path}")
            
        for path in backup_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                workflow_id = data.get("id", path.stem)
                self.save_workflow(workflow_id, data)
                count += 1
            except Exception:
                continue
                
        return count


class StorageError(Exception):
    """Exception raised for storage errors"""
    pass

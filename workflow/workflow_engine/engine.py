"""
Neshama Workflow Engine
Main entry point for the workflow execution system
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, Optional

from .parser import WorkflowParser
from .executor import WorkflowExecutor
from .scheduler import WorkflowScheduler
from .storage import WorkflowStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Main workflow engine class"""
    
    def __init__(self, storage_path: str = "./data/workflows"):
        self.storage = WorkflowStorage(storage_path)
        self.parser = WorkflowParser()
        self.executor = WorkflowExecutor()
        self.scheduler = WorkflowScheduler(self._execute_workflow)
        
        self._running = False
        self._active_workflows: Dict[str, dict] = {}
        
    def _execute_workflow(self, workflow_id: str, context: dict = None):
        """Execute a workflow by ID"""
        async def _async_execute():
            try:
                workflow_data = self.storage.load_workflow(workflow_id)
                if not workflow_data:
                    logger.error(f"Workflow {workflow_id} not found")
                    return
                    
                logger.info(f"Starting execution of workflow: {workflow_id}")
                self._active_workflows[workflow_id] = {
                    "status": "running",
                    "started_at": datetime.now().isoformat()
                }
                
                parsed = self.parser.parse(workflow_data)
                result = await self.executor.execute(parsed, context)
                
                self._active_workflows[workflow_id].update({
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "result": result
                })
                
                logger.info(f"Workflow {workflow_id} completed successfully")
                return result
                
            except Exception as e:
                logger.error(f"Error executing workflow {workflow_id}: {e}")
                self._active_workflows[workflow_id].update({
                    "status": "failed",
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                })
                raise
                
        asyncio.create_task(_async_execute())
        
    async def load_and_execute(self, workflow_id: str, context: dict = None):
        """Load workflow from storage and execute"""
        await _async_execute(workflow_id, context)
        
    def register_workflow(self, workflow_data: dict) -> str:
        """Register a new workflow"""
        workflow_id = workflow_data.get("id") or self._generate_id()
        workflow_data["id"] = workflow_id
        workflow_data["created_at"] = datetime.now().isoformat()
        workflow_data["updated_at"] = datetime.now().isoformat()
        
        self.storage.save_workflow(workflow_id, workflow_data)
        
        # Register with scheduler if has trigger
        if "trigger" in workflow_data:
            self.scheduler.register_workflow(workflow_id, workflow_data["trigger"])
            
        logger.info(f"Registered workflow: {workflow_id}")
        return workflow_id
        
    def unregister_workflow(self, workflow_id: str):
        """Unregister a workflow"""
        self.storage.delete_workflow(workflow_id)
        self.scheduler.unregister_workflow(workflow_id)
        
        if workflow_id in self._active_workflows:
            del self._active_workflows[workflow_id]
            
        logger.info(f"Unregistered workflow: {workflow_id}")
        
    def update_workflow(self, workflow_id: str, workflow_data: dict):
        """Update an existing workflow"""
        workflow_data["id"] = workflow_id
        workflow_data["updated_at"] = datetime.now().isoformat()
        
        self.storage.save_workflow(workflow_id, workflow_data)
        
        # Update scheduler
        self.scheduler.unregister_workflow(workflow_id)
        if "trigger" in workflow_data:
            self.scheduler.register_workflow(workflow_id, workflow_data["trigger"])
            
        logger.info(f"Updated workflow: {workflow_id}")
        
    def get_workflow_status(self, workflow_id: str) -> Optional[dict]:
        """Get the status of a workflow"""
        if workflow_id in self._active_workflows:
            return self._active_workflows[workflow_id]
        return self.storage.get_workflow_metadata(workflow_id)
        
    def list_workflows(self) -> list:
        """List all registered workflows"""
        return self.storage.list_workflows()
        
    def _generate_id(self) -> str:
        """Generate a unique workflow ID"""
        import uuid
        return f"wf_{uuid.uuid4().hex[:8]}"
        
    async def start(self):
        """Start the workflow engine"""
        self._running = True
        
        # Load all workflows and register scheduled ones
        workflows = self.storage.list_workflows()
        for wf in workflows:
            wf_data = self.storage.load_workflow(wf["id"])
            if wf_data and "trigger" in wf_data:
                self.scheduler.register_workflow(wf["id"], wf_data["trigger"])
                
        self.scheduler.start()
        logger.info("Workflow engine started")
        
    def stop(self):
        """Stop the workflow engine"""
        self._running = False
        self.scheduler.stop()
        logger.info("Workflow engine stopped")
        
    def export_workflow(self, workflow_id: str) -> str:
        """Export workflow as JSON string"""
        workflow = self.storage.load_workflow(workflow_id)
        if workflow:
            return json.dumps(workflow, indent=2, ensure_ascii=False)
        return None
        
    def import_workflow(self, json_str: str) -> str:
        """Import workflow from JSON string"""
        try:
            workflow_data = json.loads(json_str)
            return self.register_workflow(workflow_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
            
    def run_workflow(self, workflow_id: str, context: dict = None):
        """Manually trigger a workflow execution"""
        self._execute_workflow(workflow_id, context)


def create_engine(storage_path: str = "./data/workflows") -> WorkflowEngine:
    """Factory function to create a workflow engine"""
    return WorkflowEngine(storage_path)


def main():
    """Main entry point"""
    engine = create_engine()
    
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        engine.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run async main
    async def async_main():
        await engine.start()
        logger.info("Press Ctrl+C to stop")
        
        # Keep running
        while engine._running:
            await asyncio.sleep(1)
            
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

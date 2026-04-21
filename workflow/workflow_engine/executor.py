"""
Workflow Executor
Executes parsed workflows node by node
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum

from .parser import WorkflowParser

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowExecutor:
    """Executes parsed workflows"""
    
    def __init__(self):
        self.parser = WorkflowParser()
        self._action_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
        
    def _register_default_handlers(self):
        """Register default action handlers"""
        # These would be replaced with actual implementations
        self._action_handlers = {
            "get_weather": self._handle_get_weather,
            "get_schedule": self._handle_get_schedule,
            "get_news": self._handle_get_news,
            "send_message": self._handle_send_message,
            "save_document": self._handle_save_document,
            "get_tasks": self._handle_get_tasks,
            "get_meetings": self._handle_get_meetings,
            "get_commits": self._handle_get_commits,
            "get_user_profile": self._handle_get_user_profile,
            "update_user_preferences": self._handle_update_preferences,
        }
        
    def register_action_handler(self, action_name: str, handler: Callable):
        """Register a custom action handler"""
        self._action_handlers[action_name] = handler
        
    async def execute(
        self, 
        workflow: dict, 
        context: dict = None
    ) -> dict:
        """Execute a parsed workflow"""
        context = context or {}
        context["workflow"] = {
            "id": workflow["id"],
            "name": workflow["name"],
            "started_at": datetime.now().isoformat()
        }
        
        graph = workflow["graph"]
        node_results: Dict[str, dict] = {}
        
        # Topological sort for execution order
        execution_order = self._topological_sort(graph)
        
        logger.info(f"Executing workflow {workflow['name']} with {len(execution_order)} nodes")
        
        for node_id in execution_order:
            node = graph["nodes"][node_id]
            
            # Check if we should execute this node (depends on previous conditions)
            should_execute = await self._check_execution_condition(
                node, node_results, context
            )
            
            if not should_execute:
                node_results[node_id] = {
                    "status": ExecutionStatus.SKIPPED,
                    "skipped_at": datetime.now().isoformat()
                }
                continue
                
            # Execute the node
            try:
                result = await self._execute_node(node, node_results, context)
                node_results[node_id] = {
                    "status": ExecutionStatus.SUCCESS,
                    "result": result,
                    "completed_at": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Error executing node {node_id}: {e}")
                node_results[node_id] = {
                    "status": ExecutionStatus.FAILED,
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                }
                raise
                
        return {
            "workflow_id": workflow["id"],
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "node_results": node_results
        }
        
    def _topological_sort(self, graph: dict) -> List[str]:
        """Get nodes in topological order for execution"""
        visited = set()
        result = []
        
        def visit(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)
            
            # Visit all dependencies first
            for source_id in graph["reverse_adjacency"].get(node_id, []):
                visit(source_id)
                
            result.append(node_id)
            
        # Start from roots
        for root in graph["roots"]:
            visit(root)
            
        return result
        
    async def _check_execution_condition(
        self, 
        node: dict, 
        node_results: Dict[str, dict],
        context: dict
    ) -> bool:
        """Check if a node should be executed based on previous results"""
        node_id = node["id"]
        
        # If no incoming edges, check trigger result
        if not context.get("_trigger_executed"):
            # First node should always run
            return True
            
        # Check condition nodes from incoming edges
        incoming = context.get("_last_condition_result")
        if incoming is not None:
            # If last was a condition, check if we follow true or false path
            port = context.get("_last_condition_port")
            if node["type"] == "condition":
                return True
                
        return True
        
    async def _execute_node(
        self, 
        node: dict, 
        node_results: Dict[str, dict],
        context: dict
    ) -> Any:
        """Execute a single node"""
        node_type = node["type"]
        node_id = node["id"]
        
        logger.debug(f"Executing node {node_id} of type {node_type}")
        
        if node_type == "trigger":
            return await self._execute_trigger(node, context)
            
        elif node_type == "action":
            return await self._execute_action(node, node_results, context)
            
        elif node_type == "condition":
            return await self._execute_condition(node, node_results, context)
            
        elif node_type == "transform":
            return await self._execute_transform(node, node_results, context)
            
        else:
            raise ValueError(f"Unknown node type: {node_type}")
            
    async def _execute_trigger(self, node: dict, context: dict) -> dict:
        """Execute a trigger node"""
        context["_trigger_executed"] = True
        return {"triggered": True, "timestamp": datetime.now().isoformat()}
        
    async def _execute_action(
        self, 
        node: dict, 
        node_results: Dict[str, dict],
        context: dict
    ) -> Any:
        """Execute an action node"""
        config = node["config"]
        action_name = config["action"]
        params = config["params"]
        
        # Resolve variables in params
        resolved_params = self._resolve_params(params, node_results, context)
        
        # Get handler
        handler = self._action_handlers.get(action_name)
        if not handler:
            raise ValueError(f"No handler for action: {action_name}")
            
        # Execute handler
        if asyncio.iscoroutinefunction(handler):
            return await handler(resolved_params, context)
        else:
            return handler(resolved_params, context)
            
    async def _execute_condition(
        self, 
        node: dict, 
        node_results: Dict[str, dict],
        context: dict
    ) -> bool:
        """Execute a condition node"""
        config = node["config"]
        check = config.get("check", {})
        
        # Evaluate condition
        result = self._evaluate_condition(check, node_results, context)
        
        # Store result for next node decision
        context["_last_condition_result"] = result
        context["_last_condition_port"] = "output_true" if result else "output_false"
        
        return result
        
    async def _execute_transform(
        self, 
        node: dict, 
        node_results: Dict[str, dict],
        context: dict
    ) -> Any:
        """Execute a transform node"""
        config = node["config"]
        transform_type = config.get("transform")
        params = config.get("params", {})
        
        # Resolve variables in params
        resolved_params = self._resolve_params(params, node_results, context)
        
        if transform_type == "template":
            return self._apply_template(resolved_params.get("template", ""), context)
            
        elif transform_type == "calculate":
            return self._apply_calculations(resolved_params.get("operations", []), context)
            
        elif transform_type == "filter":
            return self._apply_filter(resolved_params, context)
            
        elif transform_type == "map":
            return self._apply_map(resolved_params, context)
            
        else:
            raise ValueError(f"Unknown transform type: {transform_type}")
            
    def _resolve_params(
        self, 
        params: dict, 
        node_results: Dict[str, dict],
        context: dict
    ) -> dict:
        """Resolve ${variable} references in parameters"""
        resolved = {}
        
        for key, value in params.items():
            if isinstance(value, str) and "${" in value:
                resolved[key] = self.parser.resolve_variables(value, {
                    **context,
                    **self._build_result_context(node_results)
                })
            elif isinstance(value, dict):
                resolved[key] = self._resolve_params(value, node_results, context)
            elif isinstance(value, list):
                resolved[key] = [
                    self.parser.resolve_variables(v, context) 
                    if isinstance(v, str) else v
                    for v in value
                ]
            else:
                resolved[key] = value
                
        return resolved
        
    def _build_result_context(self, node_results: Dict[str, dict]) -> dict:
        """Build context from previous node results"""
        context = {}
        for node_id, result in node_results.items():
            if result.get("status") == ExecutionStatus.SUCCESS:
                context[node_id] = result.get("result")
        return context
        
    def _evaluate_condition(
        self, 
        check: dict, 
        node_results: Dict[str, dict],
        context: dict
    ) -> bool:
        """Evaluate a condition check"""
        if not check:
            return True
            
        field = check.get("field")
        operator = check.get("operator")
        value = check.get("value")
        
        # Get field value from context
        field_value = self.parser._get_nested_value(context, field)
        
        if field_value is None:
            return False
            
        # Evaluate based on operator
        if operator == "eq":
            return field_value == value
        elif operator == "ne":
            return field_value != value
        elif operator == "gt":
            return field_value > value
        elif operator == "gte":
            return field_value >= value
        elif operator == "lt":
            return field_value < value
        elif operator == "lte":
            return field_value <= value
        elif operator == "in":
            return field_value in value
        elif operator == "not_in":
            return field_value not in value
        elif operator == "contains":
            return value in field_value
        elif operator == "starts_with":
            return str(field_value).startswith(value)
        elif operator == "ends_with":
            return str(field_value).endswith(value)
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False
            
    def _apply_template(self, template: str, context: dict) -> str:
        """Apply template with context values"""
        # Simple template replacement
        result = template
        
        # Replace {{variable}} patterns
        import re
        pattern = re.compile(r'\{\{([^}]+)\}\}')
        
        def replace(match):
            path = match.group(1).strip()
            value = self.parser._get_nested_value(context, path)
            return str(value) if value is not None else ""
            
        result = pattern.sub(replace, result)
        
        # Handle #each loops (simplified)
        each_pattern = re.compile(r'\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}\}', re.DOTALL)
        
        def replace_each(match):
            list_path = match.group(1)
            item_template = match.group(2)
            
            items = self.parser._get_nested_value(context, list_path)
            if not isinstance(items, list):
                return ""
                
            results = []
            for item in items:
                item_context = {**context, "this": item}
                item_result = pattern.sub(
                    lambda m: str(self.parser._get_nested_value(item_context, m.group(1).strip())) or "",
                    item_template
                )
                results.append(item_result)
                
            return "\n".join(results)
            
        result = each_pattern.sub(replace_each, result)
        
        return result
        
    def _apply_calculations(self, operations: list, context: dict) -> dict:
        """Apply calculation operations"""
        results = {}
        
        for op in operations:
            field = op.get("field")
            stat = op.get("stat")
            alias = op.get("alias", f"{field}_{stat}")
            
            data = self.parser._get_nested_value(context, field)
            
            if not isinstance(data, list):
                results[alias] = None
                continue
                
            if stat == "count":
                results[alias] = len(data)
            elif stat == "sum":
                results[alias] = sum(item.get("value", 0) for item in data if isinstance(item, dict))
            elif stat == "avg":
                values = [item.get("value", 0) for item in data if isinstance(item, dict)]
                results[alias] = sum(values) / len(values) if values else 0
            elif stat == "min":
                values = [item.get("value", 0) for item in data if isinstance(item, dict)]
                results[alias] = min(values) if values else None
            elif stat == "max":
                values = [item.get("value", 0) for item in data if isinstance(item, dict)]
                results[alias] = max(values) if values else None
                
        return results
        
    def _apply_filter(self, params: dict, context: dict) -> list:
        """Apply filter to data"""
        # Simplified implementation
        return context.get(params.get("field", "data"), [])
        
    def _apply_map(self, params: dict, context: dict) -> list:
        """Apply map transformation to data"""
        # Simplified implementation
        return context.get(params.get("field", "data"), [])
        
    # Default action handlers (stub implementations)
    
    async def _handle_get_weather(self, params: dict, context: dict) -> dict:
        """Get weather information"""
        # In real implementation, call weather API
        return {
            "city": params.get("city", "Beijing"),
            "weather": "sunny",
            "temperature": 25,
            "description": "Clear sky"
        }
        
    async def _handle_get_schedule(self, params: dict, context: dict) -> dict:
        """Get schedule information"""
        return {"schedule": [], "count": 0}
        
    async def _handle_get_news(self, params: dict, context: dict) -> dict:
        """Get news information"""
        return {"news": [], "count": 0}
        
    async def _handle_send_message(self, params: dict, context: dict) -> dict:
        """Send a message"""
        return {"sent": True, "channel": params.get("channel")}
        
    async def _handle_save_document(self, params: dict, context: dict) -> dict:
        """Save a document"""
        return {"saved": True, "path": params.get("folder")}
        
    async def _handle_get_tasks(self, params: dict, context: dict) -> dict:
        """Get tasks"""
        return {"tasks": [], "count": 0}
        
    async def _handle_get_meetings(self, params: dict, context: dict) -> dict:
        """Get meetings"""
        return {"meetings": [], "count": 0}
        
    async def _handle_get_commits(self, params: dict, context: dict) -> dict:
        """Get code commits"""
        return {"commits": [], "count": 0}
        
    async def _handle_get_user_profile(self, params: dict, context: dict) -> dict:
        """Get user profile"""
        return {"name": "User", "timezone": "Asia/Shanghai"}
        
    async def _handle_update_preferences(self, params: dict, context: dict) -> dict:
        """Update user preferences"""
        return {"updated": True}

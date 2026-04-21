"""
Workflow Parser
Parses and validates workflow definitions
"""

import re
from typing import Any, Dict, List, Optional
from datetime import datetime


class WorkflowValidationError(Exception):
    """Raised when workflow validation fails"""
    pass


class WorkflowParser:
    """Parses workflow definitions into executable format"""
    
    # Supported node types
    NODE_TYPES = {"trigger", "action", "condition", "transform"}
    
    # Required fields per node type
    NODE_REQUIRED_FIELDS = {
        "trigger": ["type"],
        "action": ["action"],
        "condition": ["condition"],
        "transform": ["transform"]
    }
    
    def __init__(self):
        self._variable_pattern = re.compile(r'\$\{([^}]+)\}')
        
    def parse(self, workflow_data: dict) -> dict:
        """Parse workflow data into executable format"""
        self._validate_workflow(workflow_data)
        
        parsed = {
            "id": workflow_data.get("id"),
            "name": workflow_data.get("name", "Unnamed Workflow"),
            "version": workflow_data.get("version", "1.0.0"),
            "trigger": self._parse_trigger(workflow_data.get("trigger", {})),
            "nodes": self._parse_nodes(workflow_data.get("nodes", [])),
            "edges": self._parse_edges(workflow_data.get("edges", [])),
            "metadata": {
                "parsed_at": datetime.now().isoformat(),
                "author": workflow_data.get("author"),
                "description": workflow_data.get("description")
            }
        }
        
        # Build execution graph
        parsed["graph"] = self._build_graph(parsed["nodes"], parsed["edges"])
        
        return parsed
        
    def _validate_workflow(self, workflow_data: dict):
        """Validate workflow structure"""
        if not workflow_data.get("name"):
            raise WorkflowValidationError("Workflow must have a name")
            
        # Validate trigger
        if "trigger" not in workflow_data:
            raise WorkflowValidationError("Workflow must have a trigger")
            
        self._validate_trigger(workflow_data["trigger"])
        
        # Validate nodes
        if not workflow_data.get("nodes"):
            raise WorkflowValidationError("Workflow must have at least one node")
            
        node_ids = set()
        for node in workflow_data["nodes"]:
            self._validate_node(node)
            if node["id"] in node_ids:
                raise WorkflowValidationError(f"Duplicate node ID: {node['id']}")
            node_ids.add(node["id"])
            
        # Validate edges
        for edge in workflow_data.get("edges", []):
            self._validate_edge(edge, node_ids)
            
    def _validate_trigger(self, trigger: dict):
        """Validate trigger configuration"""
        trigger_type = trigger.get("type")
        if trigger_type not in ["schedule", "event", "webhook"]:
            raise WorkflowValidationError(
                f"Invalid trigger type: {trigger_type}. "
                f"Must be one of: schedule, event, webhook"
            )
            
        if trigger_type == "schedule":
            if "cron" not in trigger:
                raise WorkflowValidationError(
                    "Schedule trigger must have a 'cron' expression"
                )
                
    def _validate_node(self, node: dict):
        """Validate a single node"""
        if "id" not in node:
            raise WorkflowValidationError("Node must have an 'id'")
            
        node_type = node.get("type")
        if node_type not in self.NODE_TYPES:
            raise WorkflowValidationError(
                f"Invalid node type: {node_type}. "
                f"Must be one of: {', '.join(self.NODE_TYPES)}"
            )
            
        # Check required fields
        required = self.NODE_REQUIRED_FIELDS.get(node_type, [])
        for field in required:
            if field not in node:
                raise WorkflowValidationError(
                    f"Node '{node['id']}' of type '{node_type}' "
                    f"must have a '{field}' field"
                )
                
    def _validate_edge(self, edge: dict, valid_node_ids: set):
        """Validate an edge/connection"""
        if "from" not in edge:
            raise WorkflowValidationError("Edge must have a 'from' field")
        if "to" not in edge:
            raise WorkflowValidationError("Edge must have a 'to' field")
            
        if edge["from"] not in valid_node_ids:
            raise WorkflowValidationError(
                f"Edge references unknown node: {edge['from']}"
            )
        if edge["to"] not in valid_node_ids:
            raise WorkflowValidationError(
                f"Edge references unknown node: {edge['to']}"
            )
            
    def _parse_trigger(self, trigger: dict) -> dict:
        """Parse trigger configuration"""
        parsed = {
            "type": trigger.get("type"),
            "config": {}
        }
        
        trigger_type = trigger["type"]
        
        if trigger_type == "schedule":
            parsed["config"] = {
                "cron": trigger.get("cron"),
                "timezone": trigger.get("timezone", "UTC"),
                "start_date": trigger.get("start_date"),
                "end_date": trigger.get("end_date")
            }
            
        elif trigger_type == "event":
            parsed["config"] = {
                "event": trigger.get("event"),
                "source": trigger.get("source", "any"),
                "filter": trigger.get("filter")
            }
            
        elif trigger_type == "webhook":
            parsed["config"] = {
                "path": trigger.get("path", f"/webhook/{trigger.get('event', 'default')}"),
                "method": trigger.get("method", "POST"),
                "auth": trigger.get("auth")
            }
            
        return parsed
        
    def _parse_nodes(self, nodes: List[dict]) -> List[dict]:
        """Parse all nodes"""
        return [
            self._parse_node(node)
            for node in nodes
        ]
        
    def _parse_node(self, node: dict) -> dict:
        """Parse a single node"""
        parsed = {
            "id": node["id"],
            "name": node.get("name", node.get("action", node.get("condition", "Node"))),
            "type": node["type"],
            "config": {},
            "inputs": node.get("inputs", []),
            "outputs": node.get("outputs", [])
        }
        
        node_type = node["type"]
        
        if node_type == "trigger":
            parsed["config"]["name"] = node.get("name", "Trigger")
            
        elif node_type == "action":
            parsed["config"] = {
                "action": node.get("action"),
                "params": node.get("params", {})
            }
            
        elif node_type == "condition":
            parsed["config"] = {
                "condition": node.get("condition"),
                "check": node.get("check"),
                "true_label": node.get("true_label", "Yes"),
                "false_label": node.get("false_label", "No")
            }
            
        elif node_type == "transform":
            parsed["config"] = {
                "transform": node.get("transform"),
                "params": node.get("params", {})
            }
            
        return parsed
        
    def _parse_edges(self, edges: List[dict]) -> List[dict]:
        """Parse all edges"""
        return [
            self._parse_edge(edge)
            for edge in edges
        ]
        
    def _parse_edge(self, edge: dict) -> dict:
        """Parse a single edge"""
        return {
            "from": edge["from"],
            "to": edge["to"],
            "label": edge.get("label"),
            "port": edge.get("port", "output")  # output, output_true, output_false
        }
        
    def _build_graph(self, nodes: List[dict], edges: List[dict]) -> dict:
        """Build execution graph"""
        graph = {
            "nodes": {},  # node_id -> node
            "adjacency": {},  # node_id -> list of (target_id, edge_data)
            "reverse_adjacency": {},  # node_id -> list of source_ids
            "roots": [],  # nodes with no incoming edges
            "leaves": []  # nodes with no outgoing edges
        }
        
        # Add nodes to graph
        for node in nodes:
            node_id = node["id"]
            graph["nodes"][node_id] = node
            graph["adjacency"][node_id] = []
            graph["reverse_adjacency"][node_id] = []
            
        # Add edges to graph
        for edge in edges:
            from_id = edge["from"]
            to_id = edge["to"]
            
            graph["adjacency"][from_id].append((to_id, edge))
            graph["reverse_adjacency"][to_id].append(from_id)
            
        # Find roots and leaves
        for node_id in graph["nodes"]:
            if not graph["reverse_adjacency"][node_id]:
                graph["roots"].append(node_id)
            if not graph["adjacency"][node_id]:
                graph["leaves"].append(node_id)
                
        return graph
        
    def resolve_variables(self, template: str, context: dict) -> str:
        """Resolve ${variable} patterns in a template string"""
        def replace_var(match):
            var_path = match.group(1)
            value = self._get_nested_value(context, var_path)
            return str(value) if value is not None else ""
            
        return self._variable_pattern.sub(replace_var, template)
        
    def _get_nested_value(self, obj: dict, path: str) -> Any:
        """Get nested value from dict using dot notation"""
        keys = path.split(".")
        value = obj
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

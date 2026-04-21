# Soul层 - 知识管理模块
"""
知识管理：从经验中提取、组织和融合知识

功能：
- 经验结构化存储
- 知识节点管理
- 跨领域知识连接
- 知识检索和推荐
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from enum import Enum
import uuid
import json


class KnowledgeType(Enum):
    """知识类型"""
    FACT = "fact"                 # 事实性知识
    CONCEPT = "concept"           # 概念性知识
    PROCEDURE = "procedure"       # 程序性知识
    PRINCIPLE = "principle"       # 原则性知识
    EXPERIENCE = "experience"     # 经验性知识
    INSIGHT = "insight"          # 洞察性知识


class KnowledgeConfidence(Enum):
    """知识置信度"""
    HIGH = "high"       # >0.8
    MEDIUM = "medium"   # 0.5-0.8
    LOW = "low"         # <0.5


@dataclass
class KnowledgeNode:
    """知识节点"""
    id: str
    created_at: str
    updated_at: str
    
    # 内容
    type: KnowledgeType
    content: str
    summary: str = ""
    
    # 关联
    domain: str = ""           # 领域
    tags: List[str] = field(default_factory=list)
    related_nodes: List[str] = field(default_factory=list)  # 关联节点ID
    
    # 属性
    confidence: float = 0.5     # 置信度
    importance: float = 0.5     # 重要性
    applicability: float = 0.5  # 适用性
    
    # 使用统计
    access_count: int = 0
    application_count: int = 0
    success_count: int = 0
    
    # 来源
    source_type: str = ""       # "experience", "learning", "external"
    source_context: str = ""     # 来源上下文
    
    # 元数据
    evidence: List[str] = field(default_factory=list)  # 证据列表
    notes: str = ""
    validated: bool = False
    
    @classmethod
    def create(
        cls,
        content: str,
        knowledge_type: KnowledgeType,
        domain: str = "",
        tags: List[str] = None,
        source_type: str = "experience"
    ) -> "KnowledgeNode":
        """创建知识节点"""
        node_id = f"kn_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        
        return cls(
            id=node_id,
            created_at=now,
            updated_at=now,
            type=knowledge_type,
            content=content,
            summary=content[:100] if len(content) > 100 else content,
            domain=domain,
            tags=tags or [],
            source_type=source_type
        )
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "type": self.type.value,
            "content": self.content,
            "summary": self.summary,
            "domain": self.domain,
            "tags": self.tags,
            "related_nodes": self.related_nodes,
            "confidence": self.confidence,
            "importance": self.importance,
            "applicability": self.applicability,
            "stats": {
                "access_count": self.access_count,
                "application_count": self.application_count,
                "success_count": self.success_count
            },
            "source_type": self.source_type,
            "evidence": self.evidence,
            "validated": self.validated
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "KnowledgeNode":
        data["type"] = KnowledgeType(data.get("type", "fact"))
        if "stats" in data:
            stats = data.pop("stats")
            data["access_count"] = stats.get("access_count", 0)
            data["application_count"] = stats.get("application_count", 0)
            data["success_count"] = stats.get("success_count", 0)
        return cls(**data)


@dataclass
class KnowledgeConnection:
    """知识连接"""
    id: str
    source_id: str
    target_id: str
    connection_type: str  # "causal", "analogy", "hierarchical", "temporal", "contextual"
    strength: float = 0.5
    description: str = ""
    
    @classmethod
    def create(
        cls,
        source_id: str,
        target_id: str,
        connection_type: str,
        strength: float = 0.5
    ) -> "KnowledgeConnection":
        return cls(
            id=f"conn_{uuid.uuid4().hex[:8]}",
            source_id=source_id,
            target_id=target_id,
            connection_type=connection_type,
            strength=strength
        )


class KnowledgeGraph:
    """知识图谱"""
    
    def __init__(self):
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.connections: List[KnowledgeConnection] = []
        self.domain_index: Dict[str, Set[str]] = {}  # domain -> node_ids
        self.tag_index: Dict[str, Set[str]] = {}     # tag -> node_ids
        
        # 统计
        self.total_knowledge_items = 0
        self.last_updated = datetime.now().isoformat()
    
    def add_knowledge(
        self,
        content: str,
        knowledge_type: KnowledgeType,
        domain: str = "",
        tags: List[str] = None,
        source_type: str = "experience"
    ) -> KnowledgeNode:
        """添加知识"""
        node = KnowledgeNode.create(
            content=content,
            knowledge_type=knowledge_type,
            domain=domain,
            tags=tags,
            source_type=source_type
        )
        
        # 存储
        self.nodes[node.id] = node
        self.total_knowledge_items += 1
        
        # 更新索引
        self._update_indices(node)
        
        # 尝试建立连接
        self._establish_connections(node)
        
        self.last_updated = datetime.now().isoformat()
        return node
    
    def _update_indices(self, node: KnowledgeNode):
        """更新索引"""
        # 领域索引
        if node.domain:
            if node.domain not in self.domain_index:
                self.domain_index[node.domain] = set()
            self.domain_index[node.domain].add(node.id)
        
        # 标签索引
        for tag in node.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(node.id)
    
    def _establish_connections(self, new_node: KnowledgeNode):
        """建立知识连接"""
        for existing_node in self.nodes.values():
            if existing_node.id == new_node.id:
                continue
            
            # 检查是否应该连接
            connection = self._evaluate_connection(new_node, existing_node)
            
            if connection and connection.strength > 0.3:
                self.connections.append(connection)
                new_node.related_nodes.append(existing_node.id)
                existing_node.related_nodes.append(new_node.id)
    
    def _evaluate_connection(
        self,
        node1: KnowledgeNode,
        node2: KnowledgeNode
    ) -> Optional[KnowledgeConnection]:
        """评估两个节点是否应该连接"""
        strength = 0.0
        connection_type = ""
        
        # 1. 领域相同
        if node1.domain and node1.domain == node2.domain:
            strength += 0.3
            connection_type = "contextual"
        
        # 2. 标签重叠
        common_tags = set(node1.tags) & set(node2.tags)
        if common_tags:
            strength += 0.2 * len(common_tags)
            connection_type = connection_type or "contextual"
        
        # 3. 概念相关（简单关键词匹配）
        common_keywords = self._find_common_keywords(node1.content, node2.content)
        if len(common_keywords) >= 2:
            strength += 0.3
            connection_type = connection_type or "contextual"
        
        # 4. 因果关系检测（简化）
        if any(word in node1.content for word in ["因为", "由于", "导致"]) and \
           any(word in node2.content for word in ["所以", "因此", "结果"]):
            strength += 0.4
            connection_type = "causal"
        
        # 5. 层级关系检测
        if node1.type == KnowledgeType.CONCEPT and node2.type == KnowledgeType.FACT:
            if any(word in node2.content for word in node1.tags):
                strength += 0.25
                connection_type = connection_type or "hierarchical"
        
        if strength > 0.2:
            return KnowledgeConnection.create(
                source_id=node1.id,
                target_id=node2.id,
                connection_type=connection_type or "contextual",
                strength=min(1.0, strength)
            )
        
        return None
    
    def _find_common_keywords(self, text1: str, text2: str) -> List[str]:
        """找共同关键词"""
        # 简化实现
        stopwords = {"的", "了", "是", "在", "和", "与", "或", "但", "如果", "因为"}
        
        words1 = set(w for w in text1 if len(w) > 1 and w not in stopwords)
        words2 = set(w for w in text2 if len(w) > 1 and w not in stopwords)
        
        return list(words1 & words2)
    
    def retrieve_knowledge(
        self,
        query: str,
        domain: str = None,
        tags: List[str] = None,
        knowledge_type: KnowledgeType = None,
        top_k: int = 10
    ) -> List[Tuple[KnowledgeNode, float]]:
        """检索知识"""
        candidates = list(self.nodes.values())
        
        # 过滤
        if domain:
            domain_nodes = self.domain_index.get(domain, set())
            candidates = [n for n in candidates if n.id in domain_nodes]
        
        if tags:
            tag_nodes = set()
            for tag in tags:
                tag_nodes |= self.tag_index.get(tag, set())
            candidates = [n for n in candidates if n.id in tag_nodes]
        
        if knowledge_type:
            candidates = [n for n in candidates if n.type == knowledge_type]
        
        # 计算相关性
        scored = []
        for node in candidates:
            score = self._calculate_relevance(node, query)
            if score > 0.1:
                scored.append((node, score))
        
        # 排序
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored[:top_k]
    
    def _calculate_relevance(self, node: KnowledgeNode, query: str) -> float:
        """计算相关性"""
        query_lower = query.lower()
        content_lower = node.content.lower()
        
        # 1. 内容匹配
        content_score = 0.0
        query_words = query_lower.split()
        for word in query_words:
            if word in content_lower:
                content_score += 0.3
        
        # 2. 标签匹配
        tag_score = 0.0
        for word in query_words:
            if any(word in tag for tag in node.tags):
                tag_score += 0.2
        
        # 3. 领域匹配
        domain_score = 0.3 if word in node.domain.lower() for word in query_words else 0
        
        # 4. 置信度加成
        confidence_bonus = node.confidence * 0.2
        
        # 5. 使用频率加成
        usage_bonus = min(0.1, node.access_count * 0.01)
        
        return content_score + tag_score + domain_score + confidence_bonus + usage_bonus
    
    def record_usage(self, node_id: str, success: bool = True):
        """记录知识使用"""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.access_count += 1
            node.application_count += 1
            if success:
                node.success_count += 1
            
            # 更新置信度
            if node.application_count >= 3:
                node.confidence = node.success_count / node.application_count
    
    def get_domain_knowledge(self, domain: str, limit: int = 20) -> List[KnowledgeNode]:
        """获取特定领域的知识"""
        node_ids = self.domain_index.get(domain, set())
        nodes = [self.nodes[nid] for nid in node_ids if nid in self.nodes]
        
        # 按重要性和置信度排序
        nodes.sort(key=lambda n: n.importance * n.confidence, reverse=True)
        
        return nodes[:limit]
    
    def get_related_knowledge(
        self,
        node_id: str,
        max_depth: int = 2
    ) -> Dict[str, List[KnowledgeNode]]:
        """获取相关知识（支持多跳）"""
        result = {1: [], 2: []}
        visited = {node_id}
        
        # 第一层
        node = self.nodes.get(node_id)
        if node:
            for related_id in node.related_nodes:
                if related_id in self.nodes:
                    result[1].append(self.nodes[related_id])
                    visited.add(related_id)
        
        # 第二层
        for related_id in node.related_nodes:
            related_node = self.nodes.get(related_id)
            if related_node:
                for second_related in related_node.related_nodes:
                    if second_related not in visited and second_related in self.nodes:
                        result[2].append(self.nodes[second_related])
        
        return result
    
    def get_knowledge_summary(self) -> Dict:
        """获取知识摘要"""
        type_counts = {}
        domain_counts = {}
        
        for node in self.nodes.values():
            type_counts[node.type.value] = type_counts.get(node.type.value, 0) + 1
            if node.domain:
                domain_counts[node.domain] = domain_counts.get(node.domain, 0) + 1
        
        return {
            "total_nodes": len(self.nodes),
            "total_connections": len(self.connections),
            "type_distribution": type_counts,
            "domain_distribution": dict(sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "avg_confidence": sum(n.confidence for n in self.nodes.values()) / max(1, len(self.nodes)),
            "high_confidence_count": sum(1 for n in self.nodes.values() if n.confidence > 0.8),
            "last_updated": self.last_updated
        }
    
    def export_knowledge(self) -> Dict:
        """导出知识"""
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "connections": [
                {
                    "id": c.id,
                    "source_id": c.source_id,
                    "target_id": c.target_id,
                    "type": c.connection_type,
                    "strength": c.strength
                }
                for c in self.connections
            ],
            "metadata": {
                "total_nodes": len(self.nodes),
                "total_connections": len(self.connections),
                "export_time": datetime.now().isoformat()
            }
        }
    
    def import_knowledge(self, data: Dict):
        """导入知识"""
        # 导入节点
        for node_data in data.get("nodes", []):
            node = KnowledgeNode.from_dict(node_data)
            self.nodes[node.id] = node
            self._update_indices(node)
        
        # 导入连接
        for conn_data in data.get("connections", []):
            conn = KnowledgeConnection(**conn_data)
            self.connections.append(conn)


# 全局知识图谱实例
knowledge_graph = KnowledgeGraph()


# 便捷函数
def add_knowledge(content: str, knowledge_type: str = "experience", **kwargs) -> KnowledgeNode:
    """添加知识的便捷函数"""
    return knowledge_graph.add_knowledge(
        content=content,
        knowledge_type=KnowledgeType(knowledge_type),
        **kwargs
    )


def retrieve_knowledge(query: str, **kwargs) -> List[Dict]:
    """检索知识的便捷函数"""
    results = knowledge_graph.retrieve_knowledge(query, **kwargs)
    return [
        {"node": node.to_dict(), "score": score}
        for node, score in results
    ]

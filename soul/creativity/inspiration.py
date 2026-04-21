# Soul层 - 灵感触发模块
"""
灵感触发：创意生成的核心机制

功能：
- 随机性灵感触发
- 规律性灵感触发
- 联想链生成
- 灵感质量评估
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime, timedelta
from enum import Enum
import random
import math


class AssociationType(Enum):
    """联想类型"""
    SIMILARITY = "similarity"       # 相似联想
    CONTRAST = "contrast"           # 对比联想
    CONTIGUITY = "contiguity"       # 接近联想
    CAUSALITY = "causality"         # 因果联想
    ANALOGY = "analogy"            # 类比联想


@dataclass
class Inspiration:
    """灵感"""
    id: str
    timestamp: str
    
    # 内容
    trigger_word: str
    association_type: AssociationType
    generated_ideas: List[str] = field(default_factory=list)
    
    # 质量指标
    novelty: float = 0.5     # 新颖性
    relevance: float = 0.5  # 相关性
    utility: float = 0.5    # 有用性
    surprise: float = 0.5   # 意外性
    
    # 来源信息
    source_context: str = ""
    chain_depth: int = 1
    
    @classmethod
    def create(
        cls,
        trigger_word: str,
        association_type: AssociationType,
        ideas: List[str],
        context: str = ""
    ) -> "Inspiration":
        """创建灵感"""
        import uuid
        return cls(
            id=f"insp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:4]}",
            timestamp=datetime.now().isoformat(),
            trigger_word=trigger_word,
            association_type=association_type,
            generated_ideas=ideas,
            source_context=context
        )


@dataclass
class InspirationTrigger:
    """灵感触发器配置"""
    name: str
    trigger_type: str  # "random", "keyword", "context", "schedule"
    
    # 触发条件
    keywords: List[str] = field(default_factory=list)  # 关键词触发
    probability: float = 0.1  # 随机触发概率
    min_interval_minutes: int = 30  # 最小触发间隔
    
    # 生成的配置
    association_types: List[AssociationType] = field(
        default_factory=lambda: [AssociationType.SIMILARITY]
    )
    idea_count_range: tuple = (1, 3)
    
    # 启用状态
    enabled: bool = True
    last_triggered: Optional[str] = None


class InspirationEngine:
    """灵感引擎"""
    
    def __init__(self, config: Dict = None):
        self.triggers: Dict[str, InspirationTrigger] = {}
        self.associations: Dict[str, List[str]] = {}  # 词 -> 关联词
        self.inspiration_history: List[Inspiration] = []
        self.creativity_profile: Dict[str, float] = {
            "novelty_seeking": 0.7,
            "association_breadth": 0.6,
            "divergent_thinking": 0.7,
            "convergent_thinking": 0.6
        }
        
        # 初始化默认触发器和关联
        if config:
            self.load_config(config)
        else:
            self._init_default_triggers()
            self._init_default_associations()
    
    def _init_default_triggers(self):
        """初始化默认触发器"""
        # 随机触发
        self.triggers["random_burst"] = InspirationTrigger(
            name="随机灵感爆发",
            trigger_type="random",
            probability=0.15,
            min_interval_minutes=20,
            association_types=[
                AssociationType.SIMILARITY,
                AssociationType.CONTRAST,
                AssociationType.ANALOGY
            ],
            idea_count_range=(2, 5)
        )
        
        # 关键词触发
        self.triggers["creative_keywords"] = InspirationTrigger(
            name="创意关键词触发",
            trigger_type="keyword",
            keywords=["想象", "创造", "新颖", "idea", "创意", "有趣"],
            min_interval_minutes=10,
            association_types=[
                AssociationType.SIMILARITY,
                AssociationType.ANALOGY
            ],
            idea_count_range=(1, 3)
        )
        
        # 上下文触发
        self.triggers["context_inspired"] = InspirationTrigger(
            name="上下文触发",
            trigger_type="context",
            probability=0.3,
            min_interval_minutes=15,
            association_types=[
                AssociationType.CONTIGUITY,
                AssociationType.CAUSALITY
            ],
            idea_count_range=(1, 2)
        )
    
    def _init_default_associations(self):
        """初始化默认关联网络"""
        # 通用创意关联
        common_associations = {
            # 颜色
            "红色": ["热情", "活力", "危险", "爱情", "能量", "火焰", "太阳"],
            "蓝色": ["冷静", "科技", "天空", "海洋", "深邃", "信任"],
            "绿色": ["自然", "生命", "希望", "和平", "成长", "健康"],
            
            # 抽象概念
            "时间": ["流逝", "记忆", "永恒", "瞬间", "轮回", "未来"],
            "空间": ["无限", "边界", "维度", "穿越", "距离"],
            "梦想": ["追求", "希望", "超越", "现实", "幻影", "未来"],
            
            # 情感
            "快乐": ["笑容", "阳光", "音乐", "自由", "分享", "成就感"],
            "孤独": ["寂静", "思考", "自我", "夜空", "成长"],
            "勇气": ["冒险", "挑战", "突破", "坚持", "成长"],
            
            # 日常
            "咖啡": ["清晨", "思考", "约会", "书", "香气", "悠闲"],
            "书": ["知识", "想象", "旅行", "故事", "智慧"],
            "音乐": ["情感", "节奏", "共鸣", "回忆", "表达"]
        }
        
        self.associations.update(common_associations)
    
    def load_config(self, config: Dict):
        """从配置加载"""
        if "triggers" in config:
            for trigger_data in config["triggers"]:
                trigger = InspirationTrigger(**trigger_data)
                self.triggers[trigger.name] = trigger
        
        if "associations" in config:
            self.associations.update(config["associations"])
        
        if "creativity_profile" in config:
            self.creativity_profile.update(config["creativity_profile"])
    
    def check_triggers(self, context: Dict) -> List[InspirationTrigger]:
        """检查哪些触发器应该激活"""
        active_triggers = []
        current_time = datetime.now()
        
        for trigger in self.triggers.values():
            if not trigger.enabled:
                continue
            
            # 检查间隔
            if trigger.last_triggered:
                last_time = datetime.fromisoformat(trigger.last_triggered)
                if (current_time - last_time).total_seconds() < trigger.min_interval_minutes * 60:
                    continue
            
            # 检查触发条件
            should_activate = False
            
            if trigger.trigger_type == "random":
                should_activate = random.random() < trigger.probability
            
            elif trigger.trigger_type == "keyword":
                context_text = context.get("text", "").lower()
                for keyword in trigger.keywords:
                    if keyword.lower() in context_text:
                        should_activate = True
                        break
            
            elif trigger.trigger_type == "context":
                if context.get("is_creative_topic"):
                    should_activate = random.random() < trigger.probability * 2
            
            if should_activate:
                trigger.last_triggered = current_time.isoformat()
                active_triggers.append(trigger)
        
        return active_triggers
    
    def generate_associations(
        self,
        word: str,
        association_type: AssociationType,
        max_associations: int = 5
    ) -> List[str]:
        """生成关联词"""
        associations = []
        
        # 1. 直接关联（相似）
        if association_type == AssociationType.SIMILARITY:
            if word in self.associations:
                associations.extend(self.associations[word][:max_associations])
            
            # 添加基于用户交互的关联
            recent_words = self._get_recent_context_words(word)
            associations.extend(recent_words[:3])
        
        # 2. 对比关联
        elif association_type == AssociationType.CONTRAST:
            opposites = self._get_opposites(word)
            associations.extend(opposites)
        
        # 3. 接近关联
        elif association_type == AssociationType.CONTIGUITY:
            context_words = self._get_contextually_close(word)
            associations.extend(context_words)
        
        # 4. 因果关联
        elif association_type == AssociationType.CAUSALITY:
            causes = self._get_causes(word)
            effects = self._get_effects(word)
            associations.extend(causes + effects)
        
        # 5. 类比关联
        elif association_type == AssociationType.ANALOGY:
            analogies = self._get_analogies(word)
            associations.extend(analogies)
        
        # 去重
        associations = list(dict.fromkeys(associations))[:max_associations]
        
        return associations
    
    def _get_recent_context_words(self, word: str, limit: int = 5) -> List[str]:
        """获取最近上下文相关的词"""
        # 基于最近的灵感历史
        recent = self.inspiration_history[-10:] if self.inspiration_history else []
        related = []
        
        for insp in recent:
            if word in insp.trigger_word or any(word in i for i in insp.generated_ideas):
                related.extend(insp.generated_ideas)
        
        return related[:limit]
    
    def _get_opposites(self, word: str) -> List[str]:
        """获取反义词"""
        opposites_map = {
            "快乐": ["悲伤", "痛苦", "忧郁"],
            "悲伤": ["快乐", "喜悦", "幸福"],
            "黑暗": ["光明", "阳光", "希望"],
            "光明": ["黑暗", "阴影", "未知"],
            "安静": ["喧嚣", "热闹", "嘈杂"],
            "简单": ["复杂", "困难", "繁琐"],
            "快": ["慢", "迟缓", "悠闲"],
            "慢": ["快", "迅速", "急速"]
        }
        
        return opposites_map.get(word, [])
    
    def _get_contextually_close(self, word: str) -> List[str]:
        """获取情境接近的词"""
        # 基于共现关系的简单实现
        close_map = {
            "春天": ["花开", "新生", "希望", "温暖", "色彩"],
            "夏天": ["炎热", "海滩", "西瓜", "空调", "暴雨"],
            "秋天": ["丰收", "落叶", "凉爽", "金黄", "思念"],
            "冬天": ["寒冷", "雪花", "温暖", "围炉", "新年"],
            "工作": ["压力", "成就", "同事", "项目", "Deadline"],
            "休息": ["睡眠", "放松", "旅行", "阅读", "运动"]
        }
        
        return close_map.get(word, [])
    
    def _get_causes(self, word: str) -> List[str]:
        """获取原因"""
        cause_map = {
            "成功": ["努力", "坚持", "机遇", "能力", "团队"],
            "失败": ["疏忽", "困难", "经验不足", "运气不好", "判断失误"],
            "快乐": ["成就", "关系", "健康", "满足", "惊喜"]
        }
        
        return cause_map.get(word, [])
    
    def _get_effects(self, word: str) -> List[str]:
        """获取结果"""
        effect_map = {
            "努力": ["进步", "成功", "成长", "收获", "疲惫"],
            "学习": ["知识", "技能", "成长", "理解", "证书"],
            "锻炼": ["健康", "体能", "自信", "习惯", "活力"]
        }
        
        return effect_map.get(word, [])
    
    def _get_analogies(self, word: str) -> List[str]:
        """获取类比"""
        analogy_map = {
            "人生": ["旅行", "河流", "舞台", "画卷", "马拉松"],
            "知识": ["海洋", "灯塔", "钥匙", "阶梯", "种子"],
            "思想": ["翅膀", "火焰", "种子", "星空", "源泉"],
            "时间": ["金钱", "河流", "白马", "沙漏", "光"]
        }
        
        return analogy_map.get(word, [])
    
    def create_inspiration(
        self,
        trigger_word: str,
        association_type: AssociationType,
        context: str = ""
    ) -> Inspiration:
        """创建灵感"""
        # 生成关联
        idea_count = random.randint(1, 3)
        ideas = self.generate_associations(trigger_word, association_type, idea_count)
        
        # 评估质量
        novelty = self._evaluate_novelty(ideas)
        relevance = self._evaluate_relevance(ideas, trigger_word)
        utility = self._evaluate_utility(ideas)
        surprise = self._evaluate_surprise(ideas)
        
        inspiration = Inspiration.create(
            trigger_word=trigger_word,
            association_type=association_type,
            ideas=ideas,
            context=context
        )
        inspiration.novelty = novelty
        inspiration.relevance = relevance
        inspiration.utility = utility
        inspiration.surprise = surprise
        
        # 记录
        self.inspiration_history.append(inspiration)
        
        # 限制历史长度
        if len(self.inspiration_history) > 500:
            self.inspiration_history = self.inspiration_history[-500:]
        
        return inspiration
    
    def _evaluate_novelty(self, ideas: List[str]) -> float:
        """评估新颖性"""
        if not ideas:
            return 0.0
        
        # 检查与历史的重复度
        recent_concepts = set()
        for insp in self.inspiration_history[-50:]:
            recent_concepts.update(insp.generated_ideas)
        
        novel_count = sum(1 for idea in ideas if idea not in recent_concepts)
        novelty = novel_count / len(ideas)
        
        # 加入随机因素
        novelty = novelty * 0.7 + random.random() * 0.3
        
        return min(1.0, max(0.0, novelty))
    
    def _evaluate_relevance(self, ideas: List[str], trigger: str) -> float:
        """评估相关性"""
        if not ideas:
            return 0.0
        
        # 简单的基于关联网络的相关性
        relevant_count = 0
        if trigger in self.associations:
            relevant_count = len([i for i in ideas if i in self.associations[trigger]])
        
        relevance = relevant_count / len(ideas) if ideas else 0.0
        relevance = relevance * 0.6 + 0.4
        
        return min(1.0, max(0.0, relevance))
    
    def _evaluate_utility(self, ideas: List[str]) -> float:
        """评估有用性"""
        # 简化实现：基于用户交互反馈
        return min(1.0, 0.5 + random.random() * 0.5)
    
    def _evaluate_surprise(self, ideas: List[str]) -> float:
        """评估意外性"""
        # 基于与近期上下文的差异
        return min(1.0, 0.4 + random.random() * 0.6)
    
    def get_inspiration_suggestions(
        self,
        context: Dict,
        max_suggestions: int = 3
    ) -> List[Dict]:
        """获取灵感建议"""
        # 检查触发器
        active_triggers = self.check_triggers(context)
        
        if not active_triggers:
            return []
        
        suggestions = []
        trigger_word = context.get("trigger_word", "创意")
        
        for trigger in active_triggers:
            for assoc_type in trigger.association_types:
                inspiration = self.create_inspiration(
                    trigger_word=trigger_word,
                    association_type=assoc_type,
                    context=context.get("text", "")
                )
                
                if inspiration.generated_ideas:
                    suggestions.append({
                        "id": inspiration.id,
                        "trigger": trigger.name,
                        "association_type": assoc_type.value,
                        "ideas": inspiration.generated_ideas,
                        "quality": {
                            "novelty": inspiration.novelty,
                            "relevance": inspiration.relevance,
                            "surprise": inspiration.surprise
                        }
                    })
                    
                    if len(suggestions) >= max_suggestions:
                        break
        
        return suggestions
    
    def get_inspiration_stats(self) -> Dict:
        """获取灵感统计"""
        if not self.inspiration_history:
            return {"total": 0}
        
        recent = self.inspiration_history[-50:]
        
        return {
            "total_inspirations": len(self.inspiration_history),
            "recent_count": len(recent),
            "avg_quality": {
                "novelty": sum(i.novelty for i in recent) / len(recent),
                "relevance": sum(i.relevance for i in recent) / len(recent),
                "utility": sum(i.utility for i in recent) / len(recent)
            },
            "association_type_distribution": {
                assoc_type.value: sum(1 for i in recent if i.association_type == assoc_type)
                for assoc_type in AssociationType
            }
        }


# 全局灵感引擎实例
inspiration_engine = InspirationEngine()


# 便捷函数
def trigger_inspiration(word: str, context: str = "") -> Inspiration:
    """触发灵感的便捷函数"""
    return inspiration_engine.create_inspiration(
        trigger_word=word,
        association_type=AssociationType.SIMILARITY,
        context=context
    )


def get_inspiration_suggestions(context: Dict) -> List[Dict]:
    """获取灵感建议的便捷函数"""
    return inspiration_engine.get_inspiration_suggestions(context)

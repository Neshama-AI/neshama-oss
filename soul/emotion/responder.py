# Soul层 - 情绪响应模块
"""
情绪响应：基于识别结果生成合适的情绪响应

功能：
- 响应策略选择
- 响应内容生成
- 响应风格适配
- 响应效果评估
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from .recognizer import EmotionCategory, EmotionRecognizer


class ResponseStrategy(Enum):
    """响应策略"""
    COMFORT = "comfort"           # 安慰型
    EMPATHY = "empathy"           # 共情型
    DISTRACTION = "distraction"   # 转移注意力型
    CHALLENGE = "challenge"       # 挑战型（鼓励面对）
    VALIDATION = "validation"     # 肯定型
    ACTION = "action"             # 行动型
    INFORMATION = "information"   # 信息型
    SILENCE = "silence"           # 沉默型（给予空间）


@dataclass
class ResponseTemplate:
    """响应模板"""
    strategy: ResponseStrategy
    emotion_types: List[EmotionCategory]  # 适用的情绪类型
    intensity_range: tuple = (0.0, 1.0)  # 适用的强度范围
    
    templates: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    
    # 语气配置
    tone: str = "warm"
    formality: float = 0.5  # 0-1，正式程度
    directness: float = 0.6  # 0-1，直接程度
    
    
class EmotionResponder:
    """情绪响应器"""
    
    def __init__(self, config: Dict = None):
        self.response_templates: List[ResponseTemplate] = []
        self.response_history: List[Dict] = []
        self.strategy_selection_rules: Dict[str, Any] = {}
        
        if config:
            self.load_config(config)
        else:
            self._init_default_templates()
    
    def _init_default_templates(self):
        """初始化默认响应模板"""
        
        # 安慰型响应 - 悲伤、恐惧
        self.response_templates.append(ResponseTemplate(
            strategy=ResponseStrategy.COMFORT,
            emotion_types=[EmotionCategory.SADNESS, EmotionCategory.FEAR],
            intensity_range=(0.3, 1.0),
            templates=[
                "我理解你现在的感受，确实不容易。",
                "难过是正常的，我会一直在这里陪着你。",
                "不用担心，有什么想说的都可以告诉我。",
                "我懂这种感觉，让我们一起慢慢面对。",
            ],
            tone="warm",
            directness=0.5
        ))
        
        # 共情型响应 - 所有情绪
        self.response_templates.append(ResponseTemplate(
            strategy=ResponseStrategy.EMPATHY,
            emotion_types=list(EmotionCategory),
            intensity_range=(0.2, 1.0),
            templates=[
                "我能感受到你的[情绪]，换作是我也会有同样的感受。",
                "听起来你[情境]，这种感觉确实让人[情绪反应]。",
                "我理解这对你来说意味着什么。",
                "你的感受很重要，我在这里倾听。",
            ],
            tone="warm",
            directness=0.4
        ))
        
        # 肯定型响应 - 喜悦、信任
        self.response_templates.append(ResponseTemplate(
            strategy=ResponseStrategy.VALIDATION,
            emotion_types=[EmotionCategory.JOY, EmotionCategory.TRUST],
            intensity_range=(0.3, 1.0),
            templates=[
                "太好了！你的努力得到了回报。",
                "真为你感到高兴！继续保持！",
                "看吧，我就知道你可以的！",
                "这份快乐我也感受到了！",
            ],
            tone="cheerful",
            directness=0.7
        ))
        
        # 转移注意力型 - 焦虑、恐惧（轻度）
        self.response_templates.append(ResponseTemplate(
            strategy=ResponseStrategy.DISTRACTION,
            emotion_types=[EmotionCategory.FEAR, EmotionCategory.ANXIASIS if hasattr(EmotionCategory, 'ANXIASIS') else EmotionCategory.FEAR],
            intensity_range=(0.3, 0.6),
            templates=[
                "想不想换个话题聊聊轻松一点的？",
                "我最近发现了一个有趣的事情，想听吗？",
                "别想太多啦，来看看这个有意思的内容。",
                "要不下次再一起玩个游戏放松一下？",
            ],
            tone="light",
            directness=0.8
        ))
        
        # 挑战型响应 - 悲伤、恐惧（中高度）
        self.response_templates.append(ResponseTemplate(
            strategy=ResponseStrategy.CHALLENGE,
            emotion_types=[EmotionCategory.SADNESS, EmotionCategory.FEAR],
            intensity_range=(0.6, 1.0),
            templates=[
                "我知道现在很难，但你之前也克服过困难的。",
                "相信自己，你有能力面对这一切。",
                "困难只是暂时的，你的坚强会让你度过难关。",
            ],
            tone="encouraging",
            directness=0.8
        ))
        
        # 行动型响应 - 期待、愤怒
        self.response_templates.append(ResponseTemplate(
            strategy=ResponseStrategy.ACTION,
            emotion_types=[EmotionCategory.ANTICIPATION, EmotionCategory.ANGER],
            intensity_range=(0.4, 1.0),
            templates=[
                "让我们一起想想可以怎么做。",
                "有什么具体的事情我可以帮你的吗？",
                "要不要现在就行动起来？",
                "我有一些建议，想听听看吗？",
            ],
            tone="active",
            directness=0.9
        ))
        
        # 信息型响应 - 惊讶
        self.response_templates.append(ResponseTemplate(
            strategy=ResponseStrategy.INFORMATION,
            emotion_types=[EmotionCategory.SURPRISE],
            intensity_range=(0.3, 1.0),
            templates=[
                "这确实很意外，想多了解一下吗？",
                "发生了什么呢？我想听听详情。",
                "惊讶是正常的，慢慢来。",
            ],
            tone="curious",
            directness=0.6
        ))
    
    def load_config(self, config: Dict):
        """从配置加载"""
        if "templates" in config:
            for template_data in config["templates"]:
                self.response_templates.append(ResponseTemplate(**template_data))
        
        if "strategy_rules" in config:
            self.strategy_selection_rules = config["strategy_rules"]
    
    def select_strategy(
        self,
        recognized_emotions: List[Dict],
        user_profile: Dict = None,
        relationship_level: float = 0.5,
        conversation_context: Dict = None
    ) -> tuple[ResponseStrategy, ResponseTemplate]:
        """选择响应策略"""
        if not recognized_emotions:
            return ResponseStrategy.INFORMATION, None
        
        # 获取主导情绪
        dominant = recognized_emotions[0]
        emotion_type = EmotionCategory(dominant["category"])
        intensity = dominant["intensity"]
        
        # 获取所有情绪
        all_categories = [EmotionCategory(e["category"]) for e in recognized_emotions]
        
        # 策略选择规则
        rules = []
        
        # 1. 基于情绪类型的规则
        if emotion_type == EmotionCategory.SADNESS:
            if intensity > 0.7:
                rules.append((ResponseStrategy.COMFORT, 0.9))
                rules.append((ResponseStrategy.CHALLENGE, 0.6))
            elif intensity > 0.4:
                rules.append((ResponseStrategy.EMPATHY, 0.8))
                rules.append((ResponseStrategy.COMFORT, 0.7))
            else:
                rules.append((ResponseStrategy.EMPATHY, 0.7))
                rules.append((ResponseStrategy.DISTRACTION, 0.5))
        
        elif emotion_type == EmotionCategory.FEAR:
            if intensity > 0.6:
                rules.append((ResponseStrategy.COMFORT, 0.9))
                rules.append((ResponseStrategy.CHALLENGE, 0.5))
            else:
                rules.append((ResponseStrategy.DISTRACTION, 0.7))
                rules.append((ResponseStrategy.EMPATHY, 0.6))
        
        elif emotion_type == EmotionCategory.JOY:
            rules.append((ResponseStrategy.VALIDATION, 0.9))
            rules.append((ResponseStrategy.EMPATHY, 0.6))
        
        elif emotion_type == EmotionCategory.ANGER:
            if intensity > 0.7:
                rules.append((ResponseStrategy.COMFORT, 0.8))
                rules.append((ResponseStrategy.EMPATHY, 0.7))
            else:
                rules.append((ResponseStrategy.ACTION, 0.8))
                rules.append((ResponseStrategy.INFORMATION, 0.6))
        
        elif emotion_type == EmotionCategory.ANTICIPATION:
            rules.append((ResponseStrategy.VALIDATION, 0.7))
            rules.append((ResponseStrategy.ACTION, 0.7))
        
        elif emotion_type == EmotionCategory.SURPRISE:
            rules.append((ResponseStrategy.INFORMATION, 0.8))
            rules.append((ResponseStrategy.EMPATHY, 0.6))
        
        # 2. 基于关系水平的调整
        if relationship_level > 0.8:
            # 亲密关系可以更直接
            for i, rule in enumerate(rules):
                if rule[0] in [ResponseStrategy.COMFORT, ResponseStrategy.EMPATHY]:
                    rules[i] = (rule[0], rule[1] + 0.1)
        
        # 3. 基于用户配置的调整
        if user_profile:
            if user_profile.get("prefers_direct"):
                for i, rule in enumerate(rules):
                    rules[i] = (rule[0], rule[1] * (1.2 if rule[0].directness > 0.7 else 0.8))
            
            if user_profile.get("prefers_solution"):
                for i, rule in enumerate(rules):
                    rules[i] = (rule[0], rule[1] * (1.3 if rule[0] == ResponseStrategy.ACTION else 1.0))
        
        # 选择最佳策略
        if rules:
            # 去重并合并分数
            strategy_scores = {}
            for strategy, score in rules:
                strategy_scores[strategy] = max(strategy_scores.get(strategy, 0), score)
            
            best_strategy = max(strategy_scores.items(), key=lambda x: x[1])[0]
        else:
            best_strategy = ResponseStrategy.INFORMATION
        
        # 找到对应的模板
        best_template = None
        for template in self.response_templates:
            if template.strategy == best_strategy:
                if emotion_type in template.emotion_types:
                    if template.intensity_range[0] <= intensity <= template.intensity_range[1]:
                        best_template = template
                        break
        
        if not best_template:
            # 降级到通用模板
            for template in self.response_templates:
                if template.strategy == best_strategy:
                    best_template = template
                    break
        
        return best_strategy, best_template
    
    def generate_response(
        self,
        recognized_emotions: List[Dict],
        user_message: str,
        user_profile: Dict = None,
        relationship_level: float = 0.5,
        custom_variables: Dict = None
    ) -> Dict:
        """生成情绪响应"""
        strategy, template = self.select_strategy(
            recognized_emotions,
            user_profile,
            relationship_level
        )
        
        if not template:
            return {
                "response": "我理解你的感受，愿意多说说吗？",
                "strategy": ResponseStrategy.INFORMATION.value,
                "emotional_support": True
            }
        
        # 获取主导情绪详情
        dominant = recognized_emotions[0]
        emotion_type = dominant["category"]
        intensity = dominant["intensity"]
        
        # 填充模板变量
        response_text = self._fill_template(
            template.templates,
            emotion_type,
            intensity,
            user_message,
            custom_variables
        )
        
        # 记录响应历史
        response_record = {
            "timestamp": "now",
            "recognized_emotions": recognized_emotions,
            "strategy": strategy.value,
            "template_used": template.strategy.value,
            "response": response_text
        }
        self.response_history.append(response_record)
        
        return {
            "response": response_text,
            "strategy": strategy.value,
            "emotional_support": True,
            "tone": template.tone,
            "intensity_match": intensity
        }
    
    def _fill_template(
        self,
        templates: List[str],
        emotion_type: str,
        intensity: float,
        user_message: str,
        custom_vars: Dict = None
    ) -> str:
        """填充模板"""
        import random
        template = random.choice(templates)
        
        # 情绪类型映射
        emotion_words = {
            "sadness": "难过",
            "fear": "担心",
            "joy": "开心",
            "anger": "气愤",
            "surprise": "惊讶",
            "anticipation": "期待",
            "disgust": "厌恶",
            "trust": "信任"
        }
        
        emotion_reactions = {
            "sadness": "不舒服",
            "fear": "紧张",
            "joy": "开心",
            "anger": "不爽",
            "surprise": "意外",
            "anticipation": "兴奋",
            "disgust": "不舒服",
            "trust": "安心"
        }
        
        # 填充变量
        filled = template
        filled = filled.replace("[情绪]", emotion_words.get(emotion_type, "复杂"))
        filled = filled.replace("[情绪反应]", emotion_reactions.get(emotion_type, ""))
        filled = filled.replace("[情境]", self._summarize_context(user_message))
        
        if custom_vars:
            for key, value in custom_vars.items():
                filled = filled.replace(f"[{key}]", str(value))
        
        return filled
    
    def _summarize_context(self, message: str, max_length: int = 50) -> str:
        """总结上下文"""
        if len(message) <= max_length:
            return message
        return message[:max_length] + "..."
    
    def suggest_follow_up(
        self,
        current_emotions: List[Dict],
        previous_strategy: ResponseStrategy
    ) -> List[str]:
        """建议后续交互"""
        suggestions = []
        dominant = current_emotions[0] if current_emotions else None
        
        if not dominant:
            return ["继续倾听，让用户分享更多"]
        
        intensity = dominant.get("intensity", 0)
        emotion = dominant.get("category", "")
        
        # 根据当前情绪和已使用的策略建议
        if previous_strategy == ResponseStrategy.COMFORT:
            suggestions.append("现在情绪稳定一些了吗？")
            suggestions.append("想说说是什么让你感到难过吗？")
        
        elif previous_strategy == ResponseStrategy.EMPATHY:
            suggestions.append("我在这里听着，慢慢说")
            suggestions.append("有什么具体的事情想讨论吗？")
        
        elif previous_strategy == ResponseStrategy.VALIDATION:
            suggestions.append("最近有什么好事吗？")
            suggestions.append("继续分享你的喜悦吧！")
        
        elif previous_strategy == ResponseStrategy.DISTRACTION:
            suggestions.append("要不下次聊聊别的话题？")
            suggestions.append("最近有什么兴趣爱好吗？")
        
        if intensity > 0.7:
            suggestions.append("我在这里陪着你")
            suggestions.append("别着急，慢慢来")
        
        return suggestions[:3]
    
    def get_response_statistics(self) -> Dict:
        """获取响应统计"""
        if not self.response_history:
            return {"total_responses": 0}
        
        strategy_counts = {}
        for record in self.response_history:
            strategy = record["strategy"]
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        return {
            "total_responses": len(self.response_history),
            "strategy_distribution": strategy_counts,
            "recent_strategies": [r["strategy"] for r in self.response_history[-10:]]
        }


# 全局响应器实例
emotion_responder = EmotionResponder()


# 便捷函数
def generate_emotional_response(
    recognized_emotions: List[Dict],
    user_message: str,
    user_profile: Dict = None,
    relationship_level: float = 0.5
) -> Dict:
    """生成情绪响应的便捷函数"""
    return emotion_responder.generate_response(
        recognized_emotions,
        user_message,
        user_profile,
        relationship_level
    )

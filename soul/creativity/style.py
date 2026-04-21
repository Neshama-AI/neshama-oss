# Soul层 - 创作风格养成模块
"""
创作风格养成：基于历史偏好形成独特的创作风格

功能：
- 风格特征提取
- 风格一致性维护
- 风格渐进演化
- 风格档案管理
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum
import json


class StyleDimension(Enum):
    """风格维度"""
    TONE = "tone"                   # 语气风格
    VOCABULARY = "vocabulary"       # 词汇选择
    STRUCTURE = "structure"         # 结构偏好
    PUNCTUATION = "punctuation"    # 标点风格
    EMPHASIS = "emphasis"           # 强调方式
    HUMOR = "humor"                 # 幽默程度
    SENSITIVITY = "sensitivity"     # 敏感程度
    FORMALITY = "formality"         # 正式程度


@dataclass
class StylePreference:
    """风格偏好"""
    dimension: StyleDimension
    value: float = 0.5             # 偏好值 0-1
    examples: List[str] = field(default_factory=list)
    weight: float = 1.0           # 在整体风格中的权重
    confidence: float = 0.0       # 置信度
    
    # 演化信息
    evolution_history: List[Dict] = field(default_factory=list)
    
    def update(self, new_value: float, example: str = ""):
        """更新偏好"""
        # 使用指数移动平均
        alpha = 0.3  # 平滑系数
        old_value = self.value
        self.value = alpha * new_value + (1 - alpha) * self.value
        
        # 更新置信度
        self.confidence = min(1.0, self.confidence + 0.1)
        
        # 记录历史
        if example:
            self.examples.append(example)
            if len(self.examples) > 20:
                self.examples = self.examples[-20:]
        
        self.evolution_history.append({
            "timestamp": datetime.now().isoformat(),
            "old_value": old_value,
            "new_value": self.value,
            "delta": new_value - old_value,
            "example": example
        })
        
        # 限制历史长度
        if len(self.evolution_history) > 100:
            self.evolution_history = self.evolution_history[-100:]


@dataclass
class StyleProfile:
    """风格档案"""
    id: str
    name: str
    created_at: str
    updated_at: str
    
    # 风格维度
    dimensions: Dict[str, StylePreference] = field(default_factory=dict)
    
    # 标志性特征
    signature_phrases: List[str] = field(default_factory=list)
    avoided_patterns: List[str] = field(default_factory=list)
    
    # 偏好标签
    tags: List[str] = field(default_factory=list)
    
    # 统计
    generation_count: int = 0
    user_feedback_count: int = 0
    positive_feedback_rate: float = 0.5
    
    @classmethod
    def create(cls, name: str = "Default") -> "StyleProfile":
        """创建风格档案"""
        import uuid
        profile_id = f"style_{uuid.uuid4().hex[:8]}"
        
        profile = cls(
            id=profile_id,
            name=name,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # 初始化默认维度
        for dim in StyleDimension:
            profile.dimensions[dim.value] = StylePreference(
                dimension=dim,
                value=0.5,
                confidence=0.0
            )
        
        return profile
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "dimensions": {
                name: {
                    "value": dim.value,
                    "confidence": dim.confidence,
                    "examples": dim.examples[-5:]
                }
                for name, dim in self.dimensions.items()
            },
            "signature_phrases": self.signature_phrases,
            "tags": self.tags,
            "stats": {
                "generation_count": self.generation_count,
                "user_feedback_count": self.user_feedback_count,
                "positive_feedback_rate": self.positive_feedback_rate
            }
        }


class StyleLearner:
    """风格学习器"""
    
    def __init__(self):
        self.profiles: Dict[str, StyleProfile] = {}
        self.active_profile_id: Optional[str] = None
        self.learning_history: List[Dict] = []
        
        # 初始化默认风格档案
        default_profile = StyleProfile.create("Default")
        self.profiles[default_profile.id] = default_profile
        self.active_profile_id = default_profile.id
    
    def get_active_profile(self) -> Optional[StyleProfile]:
        """获取当前活跃的风格档案"""
        if self.active_profile_id:
            return self.profiles.get(self.active_profile_id)
        return None
    
    def learn_from_generation(
        self,
        generated_content: str,
        context: Dict = None
    ):
        """从生成内容中学习"""
        profile = self.get_active_profile()
        if not profile:
            return
        
        profile.generation_count += 1
        
        # 分析内容特征
        features = self._analyze_content_features(generated_content)
        
        # 更新各维度
        for dim_name, feature_value in features.items():
            if dim_name in profile.dimensions:
                profile.dimensions[dim_name].update(
                    new_value=feature_value,
                    example=generated_content[:100]
                )
        
        # 检测标志性短语
        self._extract_signature_phrases(profile, generated_content)
        
        # 更新时间戳
        profile.updated_at = datetime.now().isoformat()
    
    def learn_from_feedback(
        self,
        content_id: str,
        feedback: Dict,
        original_content: str = ""
    ):
        """从用户反馈中学习"""
        profile = self.get_active_profile()
        if not profile:
            return
        
        profile.user_feedback_count += 1
        
        is_positive = feedback.get("is_positive", True)
        rating = feedback.get("rating", 0.5)  # 0-1
        
        # 更新正面反馈率
        prev_count = profile.user_feedback_count - 1
        profile.positive_feedback_rate = (
            (profile.positive_feedback_rate * prev_count + (1 if is_positive else 0))
            / profile.user_feedback_count
        )
        
        # 根据反馈调整
        if original_content:
            features = self._analyze_content_features(original_content)
            
            adjustment = 0.1 if is_positive else -0.1
            
            for dim_name, feature_value in features.items():
                if dim_name in profile.dimensions:
                    # 正面反馈：强化当前特征
                    # 负面反馈：弱化当前特征
                    adjusted_value = feature_value + adjustment
                    profile.dimensions[dim_name].update(
                        new_value=adjusted_value,
                        example=f"Feedback-based adjustment"
                    )
        
        # 记录学习
        self.learning_history.append({
            "timestamp": datetime.now().isoformat(),
            "content_id": content_id,
            "feedback": feedback,
            "is_positive": is_positive
        })
    
    def _analyze_content_features(self, content: str) -> Dict[str, float]:
        """分析内容特征"""
        features = {}
        
        # 语气分析
        exclamations = content.count('!')
        questions = content.count('?')
        total_sentences = max(1, content.count('.') + exclamations + questions)
        features["tone_expressive"] = min(1.0, (exclamations + questions) / total_sentences * 2)
        
        # 词汇复杂度
        words = content.split()
        avg_word_length = sum(len(w) for w in words) / max(1, len(words))
        features["vocabulary_complexity"] = min(1.0, avg_word_length / 10)
        
        # 正式程度
        informal_indicators = ["啦", "呀", "哦", "嘛", "哈", "呵呵"]
        formal_indicators = ["因此", "然而", "此外", "综上所述"]
        
        informal_count = sum(1 for ind in informal_indicators if ind in content)
        formal_count = sum(1 for ind in formal_indicators if ind in content)
        
        features["formality"] = formal_count / max(1, informal_count + formal_count + 1)
        
        # 幽默元素
        humor_indicators = ["哈哈", "笑", "有趣", "调皮", "幽默", "玩笑"]
        features["humor"] = sum(1 for ind in humor_indicators if ind in content) / max(1, len(words) / 10)
        features["humor"] = min(1.0, features["humor"])
        
        # 敏感度（委婉程度）
        softeners = ["可能", "也许", "感觉", "似乎", "大概"]
        features["sensitivity"] = sum(1 for s in softeners if s in content) / max(1, total_sentences)
        features["sensitivity"] = min(1.0, features["sensitivity"])
        
        # 结构偏好
        list_indicators = ["1.", "2.", "第一", "第二", "首先", "其次"]
        features["structure_organized"] = sum(1 for ind in list_indicators if ind in content) / max(1, len(words) / 20)
        features["structure_organized"] = min(1.0, features["structure_organized"])
        
        # 强调方式
        emphasis_indicators = ["特别", "非常", "重要", "关键", "必须", "一定"]
        features["emphasis"] = sum(1 for ind in emphasis_indicators if ind in content) / max(1, total_sentences)
        features["emphasis"] = min(1.0, features["emphasis"])
        
        return features
    
    def _extract_signature_phrases(self, profile: StyleProfile, content: str):
        """提取标志性短语"""
        # 简单的短语提取逻辑
        # 实际应用中需要更复杂的NLP处理
        
        phrases = []
        
        # 提取常见短语模式
        patterns = [
            r'.{3,10}[的|地|得].{3,10}',
            r'[我|你|他|这|那].{2,5}',
            r'.{2,5}[呀|啊|哦|吧|呢].{1,3}'
        ]
        
        import re
        for pattern in patterns:
            matches = re.findall(pattern, content)
            phrases.extend(matches)
        
        # 出现多次的短语
        phrase_counts = {}
        for phrase in phrases:
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        
        # 保留出现3次以上的
        for phrase, count in phrase_counts.items():
            if count >= 3 and len(phrase) >= 4:
                if phrase not in profile.signature_phrases:
                    profile.signature_phrases.append(phrase)
        
        # 限制数量
        if len(profile.signature_phrases) > 30:
            profile.signature_phrases = profile.signature_phrases[-30:]
    
    def apply_style(
        self,
        base_content: str,
        target_dimensions: Dict[str, float] = None
    ) -> str:
        """应用风格到内容"""
        profile = self.get_active_profile()
        if not profile:
            return base_content
        
        styled_content = base_content
        
        # 根据维度调整
        if target_dimensions:
            for dim_name, target_value in target_dimensions.items():
                if dim_name in profile.dimensions:
                    styled_content = self._adjust_dimension(
                        styled_content,
                        dim_name,
                        target_value,
                        profile.dimensions[dim_name].value
                    )
        
        return styled_content
    
    def _adjust_dimension(
        self,
        content: str,
        dimension: str,
        target_value: float,
        current_value: float
    ) -> str:
        """根据维度调整内容"""
        delta = target_value - current_value
        
        if abs(delta) < 0.1:
            return content
        
        # 简化实现
        if dimension == "formality" and delta > 0:
            # 变得更正式
            content = content.replace("啦", "").replace("呀", "")
        elif dimension == "formality" and delta < 0:
            # 变得更口语化
            pass
        
        return content
    
    def create_profile(self, name: str, template: str = "default") -> StyleProfile:
        """创建新的风格档案"""
        profile = StyleProfile.create(name)
        
        # 从模板初始化
        if template != "default":
            self._init_from_template(profile, template)
        
        self.profiles[profile.id] = profile
        return profile
    
    def _init_from_template(self, profile: StyleProfile, template: str):
        """从模板初始化"""
        templates = {
            "professional": {
                "formality": 0.8,
                "tone_expressive": 0.3,
                "humor": 0.2
            },
            "friendly": {
                "formality": 0.3,
                "tone_expressive": 0.7,
                "humor": 0.5
            },
            "creative": {
                "vocabulary_complexity": 0.7,
                "structure_organized": 0.4,
                "humor": 0.6
            }
        }
        
        if template in templates:
            for dim_name, value in templates[template].items():
                if dim_name in profile.dimensions:
                    profile.dimensions[dim_name].value = value
    
    def switch_profile(self, profile_id: str):
        """切换风格档案"""
        if profile_id in self.profiles:
            self.active_profile_id = profile_id
    
    def get_style_summary(self) -> Dict:
        """获取风格摘要"""
        profile = self.get_active_profile()
        if not profile:
            return {}
        
        top_dimensions = sorted(
            profile.dimensions.items(),
            key=lambda x: x[1].confidence * x[1].weight,
            reverse=True
        )[:5]
        
        return {
            "profile_id": profile.id,
            "profile_name": profile.name,
            "confidence_avg": sum(d.confidence for d in profile.dimensions.values()) / len(profile.dimensions),
            "top_dimensions": [
                {
                    "name": dim.value,
                    "value": pref.value,
                    "confidence": pref.confidence
                }
                for dim, pref in top_dimensions
            ],
            "signature_phrases_count": len(profile.signature_phrases),
            "stats": {
                "generations": profile.generation_count,
                "feedbacks": profile.user_feedback_count,
                "positive_rate": profile.positive_feedback_rate
            }
        }


# 全局风格学习器实例
style_learner = StyleLearner()


# 便捷函数
def learn_generation(content: str, context: Dict = None):
    """学习生成内容的便捷函数"""
    style_learner.learn_from_generation(content, context)


def apply_style(content: str, dimensions: Dict = None) -> str:
    """应用风格的便捷函数"""
    return style_learner.apply_style(content, dimensions)


def get_current_style() -> Dict:
    """获取当前风格的便捷函数"""
    return style_learner.get_style_summary()

# Soul层 - 情绪识别模块
"""
情绪识别：从输入中识别用户情绪

功能：
- 基于关键词的情绪识别
- 基于上下文的情绪推断
- 复合情绪检测
- 情绪强度评估
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import re


class EmotionCategory(Enum):
    """情绪类别"""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    AMBIGUOUS = "ambiguous"


@dataclass
class EmotionTag:
    """情绪标签"""
    category: EmotionCategory
    intensity: float = 0.5        # 强度 0-1
    confidence: float = 0.5         # 置信度 0-1
    keywords: List[str] = field(default_factory=list)
    context: str = ""              # 触发上下文


@dataclass
class EmotionPattern:
    """情绪模式"""
    name: str
    description: str
    primary_emotions: List[EmotionCategory]
    indicator_keywords: Dict[str, float]  # 关键词及其权重
    context_patterns: List[str]           # 上下文模式
    intensity_modifiers: Dict[str, float]  # 强度修饰词


class EmotionRecognizer:
    """情绪识别器"""
    
    def __init__(self, config: Dict = None):
        self.emotion_patterns: Dict[EmotionCategory, EmotionPattern] = {}
        self.intensifiers: Dict[str, float] = {}  # 强化词
        self.negators: List[str] = []  # 否定词
        
        if config:
            self.load_config(config)
        else:
            self._init_default_patterns()
    
    def _init_default_patterns(self):
        """初始化默认情绪模式"""
        
        # 快乐/喜悦
        self.emotion_patterns[EmotionCategory.JOY] = EmotionPattern(
            name="joy",
            description="快乐、满足、愉悦的情绪",
            primary_emotions=[EmotionCategory.JOY],
            indicator_keywords={
                "开心": 0.9, "高兴": 0.9, "快乐": 0.9, "喜欢": 0.7,
                "太好了": 0.95, "棒": 0.8, "完美": 0.9, "幸福": 0.9,
                "兴奋": 0.8, "满足": 0.8, "愉悦": 0.8, "happy": 0.7,
                "joy": 0.8, "wonderful": 0.9, "great": 0.7, "love": 0.8
            },
            context_patterns=[],
            intensity_modifiers={"非常": 1.3, "超级": 1.5, "有点": 0.7}
        )
        
        # 悲伤
        self.emotion_patterns[EmotionCategory.SADNESS] = EmotionPattern(
            name="sadness",
            description="悲伤、失落、难过的情绪",
            primary_emotions=[EmotionCategory.SADNESS],
            indicator_keywords={
                "难过": 0.8, "悲伤": 0.9, "伤心": 0.8, "失落": 0.8,
                "沮丧": 0.7, "郁闷": 0.7, "绝望": 0.9, "痛苦": 0.8,
                "哭": 0.7, "泪": 0.6, "难过": 0.8, "遗憾": 0.6,
                "sad": 0.7, "unhappy": 0.7, "depressed": 0.8, "crying": 0.7
            },
            context_patterns=[],
            intensity_modifiers={"非常": 1.3, "特别": 1.4, "有点": 0.6}
        )
        
        # 愤怒
        self.emotion_patterns[EmotionCategory.ANGER] = EmotionPattern(
            name="anger",
            description="愤怒、生气、恼火的情绪",
            primary_emotions=[EmotionCategory.ANGER],
            indicator_keywords={
                "生气": 0.9, "愤怒": 0.9, "恼火": 0.8, "不爽": 0.7,
                "讨厌": 0.7, "可恶": 0.8, "该死": 0.8, "混蛋": 0.7,
                "气": 0.6, "烦": 0.6, "燥": 0.6, "火": 0.6,
                "angry": 0.8, "mad": 0.7, "furious": 0.9, "hate": 0.8
            },
            context_patterns=[],
            intensity_modifiers={"非常": 1.4, "超级": 1.6, "有点": 0.5}
        )
        
        # 恐惧
        self.emotion_patterns[EmotionCategory.FEAR] = EmotionPattern(
            name="fear",
            description="恐惧、担忧、害怕的情绪",
            primary_emotions=[EmotionCategory.FEAR],
            indicator_keywords={
                "害怕": 0.9, "恐惧": 0.9, "担心": 0.7, "担忧": 0.7,
                "焦虑": 0.8, "紧张": 0.7, "不安": 0.7, "惶恐": 0.8,
                "怕": 0.6, "慌": 0.6, "惊": 0.6,
                "fear": 0.8, "scared": 0.8, "worried": 0.7, "afraid": 0.8,
                "anxious": 0.7, "nervous": 0.6
            },
            context_patterns=[],
            intensity_modifiers={"非常": 1.3, "有点": 0.6, "超级": 1.5}
        )
        
        # 惊讶
        self.emotion_patterns[EmotionCategory.SURPRISE] = EmotionPattern(
            name="surprise",
            description="惊讶、意外、震惊的情绪",
            primary_emotions=[EmotionCategory.SURPRISE],
            indicator_keywords={
                "惊讶": 0.8, "意外": 0.8, "震惊": 0.9, "吃惊": 0.8,
                "哇": 0.7, "天": 0.6, "没想到": 0.7, "居然": 0.7,
                "surprise": 0.8, "shocked": 0.9, "wow": 0.7, "amazing": 0.7
            },
            context_patterns=[],
            intensity_modifiers={"非常": 1.3, "超级": 1.5, "有点": 0.5}
        )
        
        # 厌恶
        self.emotion_patterns[EmotionCategory.DISGUST] = EmotionPattern(
            name="disgust",
            description="厌恶、反感、不屑的情绪",
            primary_emotions=[EmotionCategory.DISGUST],
            indicator_keywords={
                "恶心": 0.9, "厌恶": 0.9, "讨厌": 0.7, "反感": 0.8,
                "不屑": 0.7, "嫌弃": 0.8, "鄙视": 0.7, "烦人": 0.6,
                "disgust": 0.9, "gross": 0.8, "hate": 0.7, "terrible": 0.6
            },
            context_patterns=[],
            intensity_modifiers={"非常": 1.3, "超级": 1.5, "有点": 0.5}
        )
        
        # 信任
        self.emotion_patterns[EmotionCategory.TRUST] = EmotionPattern(
            name="trust",
            description="信任、依赖、认同的情绪",
            primary_emotions=[EmotionCategory.TRUST],
            indicator_keywords={
                "相信": 0.8, "信任": 0.9, "依赖": 0.7, "认同": 0.7,
                "肯定": 0.6, "认可": 0.7, "支持": 0.6,
                "trust": 0.8, "believe": 0.7, "rely": 0.6, "confidence": 0.7
            },
            context_patterns=[],
            intensity_modifiers={"非常": 1.3, "完全": 1.5, "有点": 0.6}
        )
        
        # 期待
        self.emotion_patterns[EmotionCategory.ANTICIPATION] = EmotionPattern(
            name="anticipation",
            description="期待、希望、渴望的情绪",
            primary_emotions=[EmotionCategory.ANTICIPATION],
            indicator_keywords={
                "期待": 0.9, "希望": 0.8, "渴望": 0.8, "盼望": 0.8,
                "想要": 0.6, "希望": 0.7, "向往": 0.7, "期望": 0.8,
                "hope": 0.8, "expect": 0.7, "looking forward": 0.8, "want": 0.6
            },
            context_patterns=[],
            intensity_modifiers={"非常": 1.3, "超级": 1.5, "有点": 0.5}
        )
        
        # 初始化强化词
        self.intensifiers = {
            "非常": 1.4, "特别": 1.4, "极其": 1.6, "超级": 1.6,
            "十分": 1.3, "相当": 1.2, "特别": 1.4, "极其": 1.6,
            "very": 1.3, "really": 1.3, "extremely": 1.5, "super": 1.5
        }
        
        # 初始化否定词
        self.negators = [
            "不", "没", "无", "非", "别", "未", "莫",
            "not", "no", "never", "don't", "didn't", "won't"
        ]
    
    def load_config(self, config: Dict):
        """从配置加载"""
        if "patterns" in config:
            for cat_str, pattern_data in config["patterns"].items():
                cat = EmotionCategory(cat_str)
                self.emotion_patterns[cat] = EmotionPattern(**pattern_data)
        
        if "intensifiers" in config:
            self.intensifiers = config["intensifiers"]
        
        if "negators" in config:
            self.negators = config["negators"]
    
    def recognize(self, text: str, context: Dict = None) -> List[EmotionTag]:
        """识别文本中的情绪"""
        if not text:
            return []
        
        text_lower = text.lower()
        text_normalized = text  # 保留原文本用于中文匹配
        
        detected_emotions = []
        
        # 1. 关键词匹配
        for category, pattern in self.emotion_patterns.items():
            max_score = 0
            matched_keywords = []
            modifier = 1.0
            
            for keyword, base_score in pattern.indicator_keywords.items():
                if keyword.lower() in text_lower or keyword in text_normalized:
                    max_score = max(max_score, base_score)
                    matched_keywords.append(keyword)
            
            # 检查强度修饰词
            for intensifier, multiplier in self.intensifiers.items():
                if intensifier in text_normalized or intensifier.lower() in text_lower:
                    modifier = multiplier
                    matched_keywords.append(intensifier)
                    break
            
            # 检查否定词（降低情绪强度或反转）
            is_negated = False
            for negator in self.negators:
                if negator in text_normalized or negator.lower() in text_lower:
                    is_negated = True
                    matched_keywords.append(negator)
                    break
            
            if max_score > 0:
                final_score = max_score * modifier
                if is_negated:
                    # 否定时，情绪强度降低或反转
                    if category in [EmotionCategory.JOY, EmotionCategory.TRUST]:
                        final_score = final_score * 0.3  # 降低正面情绪
                    else:
                        final_score = final_score * 0.5  # 其他情绪减弱
                
                # 归一化
                final_score = min(1.0, final_score)
                
                # 计算置信度（基于匹配度）
                confidence = min(1.0, len(matched_keywords) / 2 + 0.3)
                
                detected_emotions.append(EmotionTag(
                    category=category,
                    intensity=final_score,
                    confidence=confidence,
                    keywords=matched_keywords,
                    context=text_normalized[:100]
                ))
        
        # 2. 上下文增强
        if context:
            detected_emotions = self._apply_context_enhancement(detected_emotions, context)
        
        # 3. 检测复合情绪
        detected_emotions = self._detect_compound_emotions(detected_emotions)
        
        # 4. 去重和排序
        detected_emotions = self._deduplicate_emotions(detected_emotions)
        detected_emotions.sort(key=lambda x: (x.intensity * x.confidence), reverse=True)
        
        return detected_emotions
    
    def _apply_context_enhancement(self, emotions: List[EmotionTag], context: Dict) -> List[EmotionTag]:
        """根据上下文增强情绪识别"""
        conversation_tone = context.get("conversation_tone", "neutral")
        user_profile = context.get("user_profile", {})
        relationship_level = context.get("relationship_level", 0.5)
        
        # 根据对话基调调整
        if conversation_tone == "serious":
            for emotion in emotions:
                if emotion.category == EmotionCategory.JOY:
                    emotion.intensity *= 0.8
                elif emotion.category in [EmotionCategory.SADNESS, EmotionCategory.ANGER]:
                    emotion.intensity *= 1.2
        
        # 根据关系水平调整
        if relationship_level > 0.7:
            for emotion in emotions:
                if emotion.category in [EmotionCategory.SADNESS, EmotionCategory.FEAR]:
                    emotion.intensity *= 1.1  # 更敏感地回应亲密用户的负面情绪
        
        return emotions
    
    def _detect_compound_emotions(self, emotions: List[EmotionTag]) -> List[EmotionTag]:
        """检测复合情绪"""
        categories = {e.category for e in emotions}
        
        # 焦虑 = 恐惧 + 期待
        if EmotionCategory.FEAR in categories and EmotionCategory.ANTICIPATION in categories:
            fear_emo = next(e for e in emotions if e.category == EmotionCategory.FEAR)
            ant_emo = next(e for e in emotions if e.category == EmotionCategory.ANTICIPATION)
            emotions.append(EmotionTag(
                category=EmotionCategory.AMBIGUOUS,
                intensity=(fear_emo.intensity + ant_emo.intensity) / 2,
                confidence=0.6,
                keywords=["焦虑", "忐忑"],
                context="复合情绪：恐惧+期待"
            ))
        
        # 感激 = 快乐 + 信任
        if EmotionCategory.JOY in categories and EmotionCategory.TRUST in categories:
            joy_emo = next(e for e in emotions if e.category == EmotionCategory.JOY)
            trust_emo = next(e for e in emotions if e.category == EmotionCategory.TRUST)
            emotions.append(EmotionTag(
                category=EmotionCategory.JOY,
                intensity=(joy_emo.intensity + trust_emo.intensity) / 2 * 1.1,
                confidence=0.65,
                keywords=["感激", "感恩"],
                context="复合情绪：快乐+信任"
            ))
        
        return emotions
    
    def _deduplicate_emotions(self, emotions: List[EmotionTag]) -> List[EmotionTag]:
        """去重情绪（保留最高强度的）"""
        seen = {}
        for emotion in emotions:
            cat = emotion.category
            if cat not in seen or emotion.intensity > seen[cat].intensity:
                seen[cat] = emotion
        
        return list(seen.values())
    
    def recognize_from_interaction(self, interaction: Dict) -> Dict:
        """从交互历史中识别情绪"""
        user_message = interaction.get("user_message", "")
        message_history = interaction.get("message_history", [])
        
        # 分析当前消息
        current_emotions = self.recognize(user_message)
        
        # 分析上下文
        context = {
            "conversation_tone": self._analyze_conversation_tone(message_history),
            "emotional_trend": self._analyze_emotional_trend(message_history[-5:])
        }
        
        return {
            "current_emotions": [
                {
                    "category": e.category.value,
                    "intensity": e.intensity,
                    "confidence": e.confidence,
                    "keywords": e.keywords
                }
                for e in current_emotions
            ],
            "dominant_emotion": current_emotions[0].category.value if current_emotions else None,
            "overall_intensity": max([e.intensity for e in current_emotions], default=0),
            "context": context
        }
    
    def _analyze_conversation_tone(self, message_history: List[Dict]) -> str:
        """分析对话基调"""
        if not message_history:
            return "neutral"
        
        positive_count = 0
        negative_count = 0
        
        for msg in message_history[-3:]:
            emotions = self.recognize(msg.get("content", ""))
            for e in emotions:
                if e.intensity > 0.5:
                    if e.category in [EmotionCategory.JOY, EmotionCategory.TRUST]:
                        positive_count += 1
                    else:
                        negative_count += 1
        
        if positive_count > negative_count * 2:
            return "positive"
        elif negative_count > positive_count * 2:
            return "negative"
        else:
            return "neutral"
    
    def _analyze_emotional_trend(self, recent_messages: List[Dict]) -> str:
        """分析情绪趋势"""
        if len(recent_messages) < 2:
            return "stable"
        
        intensities = []
        for msg in recent_messages:
            emotions = self.recognize(msg.get("content", ""))
            if emotions:
                intensities.append(max(e.intensity for e in emotions))
            else:
                intensities.append(0)
        
        if all(intensities[i] >= intensities[i+1] for i in range(len(intensities)-1)):
            return "declining"
        elif all(intensities[i] <= intensities[i+1] for i in range(len(intensities)-1)):
            return "rising"
        else:
            return "fluctuating"


# 全局识别器实例
emotion_recognizer = EmotionRecognizer()


# 便捷函数
def recognize_emotion(text: str, context: Dict = None) -> List[Dict]:
    """识别人脸的便捷函数"""
    tags = emotion_recognizer.recognize(text, context)
    return [
        {
            "category": tag.category.value,
            "intensity": tag.intensity,
            "confidence": tag.confidence,
            "keywords": tag.keywords
        }
        for tag in tags
    ]

# Soul层 - Emotion子模块
"""
情绪系统模块

包含：
- recognizer.py - 情绪识别
- responder.py - 情绪响应
- memory.py - 情绪记忆
"""

from .recognizer import (
    EmotionRecognizer,
    EmotionCategory,
    EmotionTag,
    EmotionPattern,
    emotion_recognizer,
    recognize_emotion
)

from .responder import (
    EmotionResponder,
    ResponseStrategy,
    ResponseTemplate,
    emotion_responder,
    generate_emotional_response
)

from .memory import (
    EmotionMemory,
    EmotionEvent,
    EmotionPattern as EmotionPatternData,
    EmotionPatternType,
    get_emotion_memory,
    record_emotion
)

__all__ = [
    # Recognizer
    "EmotionRecognizer",
    "EmotionCategory",
    "EmotionTag",
    "EmotionPattern",
    "emotion_recognizer",
    "recognize_emotion",
    
    # Responder
    "EmotionResponder",
    "ResponseStrategy",
    "ResponseTemplate",
    "emotion_responder",
    "generate_emotional_response",
    
    # Memory
    "EmotionMemory",
    "EmotionEvent",
    "EmotionPatternType",
    "get_emotion_memory",
    "record_emotion"
]

#!/usr/bin/env python3
"""
Neshama Core - 带 Soul 的对话示例
===================================

演示如何使用 Soul 配置来定制 Agent 行为。

运行方式：
    python soul_chat.py
"""

import sys
import os

# 添加项目根目录到路径
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_parent_dir = os.path.dirname(_project_root)  # 获取父目录
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from Neshama.core import NeshamaEngine, EngineConfig
from Neshama.soul import SoulLoader, SoulLoaderConfig


def example_default_soul():
    """使用默认 Soul 配置"""
    print("\n" + "=" * 60)
    print("示例1: 使用默认 Soul 配置")
    print("=" * 60)
    
    engine = NeshamaEngine()
    
    print(f"\nSoul 信息:")
    print(f"  名称: {engine.soul_config.get('name')}")
    print(f"  描述: {engine.soul_config.get('description')}")
    print(f"  版本: {engine.soul_config.get('version')}")
    
    # 显示特性
    characteristics = engine.soul_config.get("characteristics", {})
    print(f"\n人格特性:")
    for name, data in characteristics.items():
        level = data.get("level", 0.5)
        desc = data.get("description", "")
        bar = "█" * int(level * 10) + "░" * (10 - int(level * 10))
        print(f"  {name}: {bar} {level:.0%} - {desc}")
    
    # 对话测试
    print(f"\n对话测试:")
    response = engine.chat("你好，你是一个什么样的AI？")
    print(f"  用户: 你好，你是一个什么样的AI？")
    print(f"  助手: {response.content[:100]}...")
    
    return engine


def example_custom_soul():
    """使用自定义 Soul 配置"""
    print("\n" + "=" * 60)
    print("示例2: 使用自定义 Soul 配置")
    print("=" * 60)
    
    # 创建自定义配置
    custom_soul = {
        "name": "Python Tutor",
        "version": "1.0.0",
        "description": "专业的Python编程导师",
        "characteristics": {
            "willpower": {"level": 0.9, "description": "耐心指导学生"},
            "execution": {"level": 0.8, "description": "高效讲解代码"},
            "empathy": {"level": 0.7, "description": "理解学生困惑"},
            "humor": {"level": 0.3, "description": "适度幽默"},
            "habits": {"level": 0.5, "description": "灵活教学"}
        },
        "behavior_patterns": {
            "response_style": {
                "verbosity": "detailed",
                "formality": "semi-formal",
                "emotional_expression": 0.4
            }
        }
    }
    
    # 创建引擎并更新配置
    engine = NeshamaEngine()
    engine.update_soul(custom_soul)
    
    print(f"\n自定义 Soul:")
    print(f"  名称: {engine.soul_config.get('name')}")
    print(f"  描述: {engine.soul_config.get('description')}")
    
    # 对话测试
    print(f"\n对话测试:")
    response = engine.chat("我不懂什么是变量，你能解释一下吗？")
    print(f"  用户: 我不懂什么是变量，你能解释一下吗？")
    print(f"  助手: {response.content[:150]}...")
    
    return engine


def example_system_prompt():
    """使用自定义系统提示词"""
    print("\n" + "=" * 60)
    print("示例3: 使用自定义系统提示词")
    print("=" * 60)
    
    config = EngineConfig(
        engine_id="creative_assistant",
        system_prompt="""你是一个创意写作助手。
        
风格要求：
- 语言优美，富有诗意
- 善于使用比喻和修辞
- 保持神秘感和想象力
- 适当使用问句引发思考

你的任务是根据用户的需求创作故事、诗歌或其他文学作品。""",
        temperature=0.9  # 高温度以获得更有创意的回答
    )
    
    engine = NeshamaEngine(config=config)
    
    print(f"\n系统提示词预览:")
    print(f"  {engine.system_prompt[:150]}...")
    
    # 对话测试
    print(f"\n对话测试:")
    response = engine.chat("写一首关于秋天的诗")
    print(f"  用户: 写一首关于秋天的诗")
    print(f"  助手:\n{response.content}")
    
    return engine


def example_soul_loader():
    """演示 SoulLoader 的使用"""
    print("\n" + "=" * 60)
    print("示例4: 使用 SoulLoader 加载配置文件")
    print("=" * 60)
    
    # 创建 Loader
    loader_config = SoulLoaderConfig(
        config_dir="./Neshama/soul",
        default_config_name="soul.yaml"
    )
    loader = SoulLoader(config=loader_config)
    
    # 加载配置
    soul_config = loader.load()
    
    print(f"\n加载的 Soul 配置:")
    print(f"  名称: {soul_config.get('name')}")
    print(f"  版本: {soul_config.get('version')}")
    
    # 创建引擎
    engine = NeshamaEngine(soul_loader=loader)
    
    # 对话测试
    print(f"\n对话测试:")
    response = engine.chat("你好！")
    print(f"  用户: 你好！")
    print(f"  助手: {response.content[:100]}...")
    
    return engine


def example_memory_with_soul():
    """演示 Soul 与 Memory 结合使用"""
    print("\n" + "=" * 60)
    print("示例5: Soul 与 Memory 结合使用")
    print("=" * 60)
    
    engine = NeshamaEngine()
    
    # 添加个人知识
    print("\n添加个人知识...")
    engine.add_knowledge(
        content="用户叫小明，是一名Python初学者，正在学习基础语法。",
        source="user_profile",
        metadata={"type": "profile"}
    )
    engine.add_knowledge(
        content="Python中的变量不需要声明类型，直接赋值即可使用。",
        source="python_basics",
        metadata={"type": "tutorial"}
    )
    engine.add_knowledge(
        content="用户喜欢简洁明了的解释，不喜欢太长的回复。",
        source="preference",
        metadata={"type": "preference"}
    )
    
    # 搜索相关知识
    print("搜索知识...")
    results = engine.search_knowledge("Python变量")
    print(f"  找到 {len(results)} 条相关知识")
    
    # 对话测试
    print("\n对话测试:")
    response = engine.chat("Python中的变量怎么用？")
    print(f"  用户: Python中的变量怎么用？")
    print(f"  助手: {response.content[:150]}...")
    
    # 显示引擎统计
    print("\n引擎统计:")
    stats = engine.get_stats()
    print(f"  引擎ID: {stats['engine_id']}")
    print(f"  Soul名称: {stats['soul_name']}")
    print(f"  会话数: {stats['session_count']}")
    memory_stats = stats.get('memory_stats', {})
    print(f"  记忆统计: {memory_stats}")
    
    return engine


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Neshama Engine - Soul 配置示例")
    print("=" * 60)
    
    # 示例1: 默认 Soul
    example_default_soul()
    
    # 示例2: 自定义 Soul
    example_custom_soul()
    
    # 示例3: 自定义系统提示词
    example_system_prompt()
    
    # 示例4: SoulLoader
    example_soul_loader()
    
    # 示例5: Soul 与 Memory 结合
    example_memory_with_soul()
    
    print("\n" + "=" * 60)
    print("所有示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

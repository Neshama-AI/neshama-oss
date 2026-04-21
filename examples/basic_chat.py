#!/usr/bin/env python3
"""
Neshama Core - 基础对话示例
============================

最简单的基础对话示例，演示如何使用 NeshamaEngine。

运行方式：
    python basic_chat.py

注意：
    首次运行会自动创建内存存储目录。
    如果没有配置 API key，会使用模拟响应模式。
"""

import sys
import os

# 添加项目根目录到路径
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_parent_dir = os.path.dirname(_project_root)  # 获取父目录
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from Neshama.core import NeshamaEngine, EngineConfig


def main():
    """基础对话示例"""
    
    print("=" * 60)
    print("Neshama Engine - 基础对话示例")
    print("=" * 60)
    print()
    
    # 方式1: 使用默认配置
    print(">>> 方式1: 使用默认配置")
    print("-" * 40)
    
    engine = NeshamaEngine()
    print(f"引擎: {engine}")
    print()
    
    # 单轮对话
    response = engine.chat("你好！")
    print(f"用户: 你好！")
    print(f"助手: {response.content}")
    print()
    
    # 方式2: 自定义配置
    print(">>> 方式2: 自定义配置")
    print("-" * 40)
    
    config = EngineConfig(
        engine_id="my_chatbot",
        engine_name="My Chatbot",
        system_prompt="你是一个乐于助人的Python编程助手。",
        model_provider="dashscope",
        model_name="qwen-plus",
        temperature=0.8,
        debug=False
    )
    
    engine2 = NeshamaEngine(config=config)
    response = engine2.chat("Python是什么？")
    print(f"用户: Python是什么？")
    print(f"助手: {response.content[:100]}...")
    print()
    
    # 方式3: 多轮对话
    print(">>> 方式3: 多轮对话")
    print("-" * 40)
    
    session = engine.create_session(user_id="demo_user")
    print(f"创建会话: {session.id}")
    print()
    
    # 第一轮
    r1 = engine.chat("我想学习编程", session_id=session.id)
    print(f"用户: 我想学习编程")
    print(f"助手: {r1.content[:80]}...")
    print()
    
    # 第二轮
    r2 = engine.chat("从哪里开始？", session_id=session.id)
    print(f"用户: 从哪里开始？")
    print(f"助手: {r2.content[:80]}...")
    print()
    
    # 第三轮
    r3 = engine.chat("推荐哪些学习资源？", session_id=session.id)
    print(f"用户: 推荐哪些学习资源？")
    print(f"助手: {r3.content[:80]}...")
    print()
    
    # 查看会话历史
    print(">>> 会话历史")
    print("-" * 40)
    history = session.get_history()
    print(f"共 {len(history)} 条消息:")
    for i, msg in enumerate(history, 1):
        role = "用户" if msg["role"] == "user" else "助手"
        content = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
        print(f"  {i}. [{role}] {content}")
    print()
    
    # 响应详情
    print(">>> 响应详情")
    print("-" * 40)
    print(f"  会话ID: {r3.session_id}")
    print(f"  消息ID: {r3.message_id}")
    print(f"  模型: {r3.model}")
    print(f"  提供商: {r3.provider}")
    print(f"  延迟: {r3.latency_ms:.0f}ms")
    print(f"  Token使用: {r3.usage}")
    print()
    
    # 引擎统计
    print(">>> 引擎统计")
    print("-" * 40)
    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    print("=" * 60)
    print("示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

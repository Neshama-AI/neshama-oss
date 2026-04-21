"""
Neshama Model Adapter - Examples
使用示例

演示 Model Adapter 的各种用法
"""

import asyncio
from model_adapter import (
    ModelAdapter, 
    Message, 
    MessageRole, 
    ModelResponse,
    RouterStrategy,
    Config
)
from model_adapter.providers import OpenAIProvider, DashScopeProvider


def example_basic_chat():
    """基础对话示例"""
    print("=== 基础对话示例 ===")
    
    # 创建适配器 (会自动从环境变量读取配置)
    adapter = ModelAdapter()
    
    # 简单对话
    response = adapter.chat_sync(
        prompt="你好，请介绍一下你自己",
        system="你是一个友好的AI助手"
    )
    
    print(f"Response: {response.content}")
    print(f"Model: {response.model}")
    print(f"Provider: {response.provider}")
    print(f"Latency: {response.latency_ms}ms")
    print()


def example_multi_turn_conversation():
    """多轮对话示例"""
    print("=== 多轮对话示例 ===")
    
    adapter = ModelAdapter()
    
    # 构建多轮对话
    messages = [
        Message(
            role=MessageRole.SYSTEM,
            content="你是一个专业的Python编程助手"
        ),
        Message(
            role=MessageRole.USER,
            content="如何用Python实现快速排序？"
        ),
        Message(
            role=MessageRole.ASSISTANT,
            content="当然可以！快速排序是一种高效的排序算法..."
        ),
        Message(
            role=MessageRole.USER,
            content="能否给出一个完整代码示例？"
        )
    ]
    
    response = adapter.call_sync(messages)
    print(f"Response: {response.content}")
    print()


async def example_async_stream():
    """异步流式响应示例"""
    print("=== 异步流式响应示例 ===")
    
    adapter = ModelAdapter()
    
    messages = [
        Message(
            role=MessageRole.USER,
            content="请写一首关于春天的诗，要求至少10行"
        )
    ]
    
    print("Streaming response:")
    collected_content = []
    
    async for chunk in adapter.call_stream(messages, model="gpt-4o"):
        if chunk.delta:
            print(chunk.delta, end="", flush=True)
            collected_content.append(chunk.delta)
    
    print("\n")
    print(f"Total tokens collected: {len(''.join(collected_content))}")
    print()


def example_specify_provider():
    """指定 Provider 示例"""
    print("=== 指定 Provider 示例 ===")
    
    adapter = ModelAdapter()
    
    # 使用阿里云百炼
    response = adapter.call_sync(
        messages=[Message(role=MessageRole.USER, content="你好")],
        provider="dashscope",
        model="qwen-plus"
    )
    
    print(f"Provider: {response.provider}")
    print(f"Model: {response.model}")
    print(f"Content: {response.content[:100]}...")
    print()


def example_custom_config():
    """自定义配置示例"""
    print("=== 自定义配置示例 ===")
    
    # 创建自定义配置
    config = Config()
    config._config["default_model"] = "qwen-plus"
    
    # 创建自定义适配器
    adapter = ModelAdapter(config=config)
    
    response = adapter.chat_sync(prompt="测试消息")
    print(f"Default model: {adapter.get_default_model()}")
    print(f"Response: {response.content[:100]}...")
    print()


def example_router_stats():
    """路由统计示例"""
    print("=== 路由统计示例 ===")
    
    adapter = ModelAdapter()
    
    # 获取统计信息
    stats = adapter.get_stats()
    
    print(f"Default model: {stats['default_model']}")
    print("\nProviders:")
    for name, provider_stats in stats['providers'].items():
        print(f"  {name}: {provider_stats}")
    
    print("\nRouter:")
    router_stats = stats['router']
    print(f"  Strategy: {router_stats['strategy']}")
    print(f"  Total models: {router_stats['total_models']}")
    print()


def example_model_pool():
    """模型池示例 - 使用不同优先级的模型"""
    print("=== 模型池示例 ===")
    
    # 使用故障转移策略
    adapter = ModelAdapter()
    # adapter.router.strategy = RouterStrategy.FAILOVER
    
    messages = [Message(role=MessageRole.USER, content="测试")]
    
    # 会自动按优先级选择可用的模型
    response = adapter.call_sync(messages)
    
    print(f"Selected model: {response.model}")
    print(f"Selected provider: {response.provider}")
    print()


async def example_all_providers():
    """测试所有 Provider 健康状态"""
    print("=== Provider 健康检查 ===")
    
    adapter = ModelAdapter()
    
    # 健康检查
    results = await adapter.health_check()
    
    for provider, is_healthy in results.items():
        if isinstance(is_healthy, dict):
            for model, status in is_healthy.items():
                print(f"  {provider}/{model}: {'✓' if status else '✗'}")
        else:
            print(f"  {provider}: {'✓' if is_healthy else '✗'}")


def example_function_calling():
    """函数调用示例（模拟）"""
    print("=== 函数调用示例 ===")
    
    adapter = ModelAdapter()
    
    # 定义工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "城市名称"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]
    
    messages = [
        Message(
            role=MessageRole.USER,
            content="北京今天天气怎么样？"
        )
    ]
    
    response = adapter.call_sync(
        messages,
        model="gpt-4o",
        tools=tools
    )
    
    print(f"Response: {response.content}")
    if response.tool_calls:
        print(f"Tool calls: {response.tool_calls}")
    print()


def main():
    """运行所有示例"""
    print("\n" + "="*50)
    print("Neshama Model Adapter Examples")
    print("="*50 + "\n")
    
    # 同步示例
    example_basic_chat()
    example_multi_turn_conversation()
    example_specify_provider()
    example_custom_config()
    example_router_stats()
    example_model_pool()
    example_function_calling()
    
    # 异步示例
    asyncio.run(example_async_stream())
    asyncio.run(example_all_providers())
    
    print("\n" + "="*50)
    print("All examples completed!")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()

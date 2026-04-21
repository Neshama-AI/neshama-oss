"""
Neshama Core - 核心对话引擎
============================

核心引擎实现，负责串联各个模块完成对话流程。

流程：
1. 加载/解析用户输入
2. 检索 Memory (RAG + 上下文)
3. 获取 Soul 配置
4. 构建 Prompt (注入 Soul + Memory)
5. 调用 LLM
6. 生成回复
7. 存储对话记忆
"""

import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime

# 导入 Soul 层 - 只导入 loader 模块避免子模块语法错误
from ..soul.loader import SoulLoader, SoulLoaderConfig

# 导入 Memory 层
from ..memory import Memory, MemoryConfig

# 导入 Model Adapter 层
from ..model_adapter import ModelAdapter, Config as ModelConfig
from ..model_adapter.providers.base import Message, MessageRole, ModelResponse

from .conversation import ConversationManager, Session

logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    """引擎配置"""
    # 引擎标识
    engine_id: str = "default"
    engine_name: str = "Neshama"
    
    # Soul 配置
    soul_config_path: Optional[str] = None
    soul_enabled: bool = True
    
    # Memory 配置
    memory_enabled: bool = True
    memory_storage_path: str = "./memory_data"
    rag_top_k: int = 3
    short_term_capacity: int = 10
    
    # Model 配置
    model_provider: str = "dashscope"  # 默认使用百炼
    model_name: str = "qwen-plus"
    temperature: float = 0.7
    max_tokens: int = 2048
    
    # 系统提示词
    system_prompt: str = "你是一个友好的AI助手。"
    
    # 调试选项
    debug: bool = False
    log_prompts: bool = False


@dataclass
class ChatResponse:
    """对话响应"""
    content: str
    session_id: str
    message_id: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    })
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def __str__(self) -> str:
        return self.content


class NeshamaEngine:
    """
    Neshama 核心对话引擎
    
    串联 Soul、Memory、Model Adapter 三个核心层，
    提供完整的对话能力。
    
    使用示例：
        # 基础用法
        engine = NeshamaEngine()
        response = engine.chat("你好")
        print(response.content)
        
        # 高级配置
        config = EngineConfig(
            soul_config_path="./configs/my_soul.yaml",
            model_provider="openai",
            model_name="gpt-4",
            debug=True
        )
        engine = NeshamaEngine(config=config)
        
        # 多轮对话
        session = engine.create_session(user_id="user123")
        response1 = engine.chat("你好", session_id=session.id)
        response2 = engine.chat("今天天气怎么样？", session_id=session.id)
        
        # 带 Memory 检索的对话
        engine.add_knowledge("Python是一种编程语言", source="编程基础")
        response = engine.chat("Python能做什么？")
    """
    
    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        model_adapter: Optional[ModelAdapter] = None,
        memory: Optional[Memory] = None,
        soul_loader: Optional[SoulLoader] = None,
    ):
        """
        初始化 Neshama 引擎
        
        Args:
            config: 引擎配置
            model_adapter: 模型适配器实例（可选，默认自动创建）
            memory: 记忆实例（可选，默认自动创建）
            soul_loader: Soul加载器实例（可选，默认自动创建）
        """
        self.config = config or EngineConfig()
        self._init_logging()
        
        logger.info(f"Initializing NeshamaEngine: {self.config.engine_id}")
        start_time = time.time()
        
        # 初始化 Soul 层
        self._init_soul(soul_loader)
        
        # 初始化 Memory 层
        self._init_memory(memory)
        
        # 初始化 Model Adapter 层
        self._init_model_adapter(model_adapter)
        
        # 初始化 Conversation Manager
        self._init_conversation_manager()
        
        logger.info(f"NeshamaEngine initialized in {time.time() - start_time:.2f}s")
    
    def _init_logging(self):
        """初始化日志"""
        if self.config.debug:
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
    
    def _init_soul(self, soul_loader: Optional[SoulLoader] = None):
        """初始化 Soul 层"""
        logger.info("Initializing Soul layer...")
        
        if soul_loader is not None:
            self.soul_loader = soul_loader
            self.soul_config = soul_loader.load()
        else:
            # 创建默认的 SoulLoader
            soul_config = SoulLoaderConfig(
                config_dir="./Neshama/soul",
                default_config_name="soul.yaml",
            )
            self.soul_loader = SoulLoader(config=soul_config)
            
            # 加载配置
            if self.config.soul_config_path:
                self.soul_config = self.soul_loader.load(self.config.soul_config_path)
            else:
                self.soul_config = self.soul_loader.load()
        
        # 提取系统提示词
        self._build_system_prompt()
        
        logger.info(f"Soul loaded: {self.soul_config.get('name', 'Unknown')}")
    
    def _build_system_prompt(self):
        """从 Soul 配置构建系统提示词"""
        if not self.config.soul_enabled:
            self.system_prompt = self.config.system_prompt
            return
        
        parts = []
        
        # 基础系统提示
        parts.append(self.config.system_prompt)
        
        # 添加 Soul 配置中的特性
        soul_info = []
        
        # 人格特征
        characteristics = self.soul_config.get("characteristics", {})
        if characteristics:
            parts.append("\n## 你的性格特点：")
            for key, value in characteristics.items():
                if isinstance(value, dict):
                    level = value.get("level", 0.5)
                    desc = value.get("description", "")
                    parts.append(f"- {key}: {desc} (自信度: {level:.0%})")
        
        # 行为模式
        behavior = self.soul_config.get("behavior_patterns", {})
        if behavior:
            parts.append("\n## 行为风格：")
            response_style = behavior.get("response_style", {})
            if response_style:
                verbosity = response_style.get("verbosity", "moderate")
                formality = response_style.get("formality", "casual")
                parts.append(f"- 回答风格: {verbosity}")
                parts.append(f"- 语气: {formality}")
        
        # 模块配置
        modules = self.soul_config.get("modules", {})
        if modules:
            creativity = modules.get("creativity", {})
            if creativity:
                level = creativity.get("creativity_level", 0.5)
                parts.append(f"\n- 创造力水平: {level:.0%}")
        
        self.system_prompt = "\n".join(parts)
        
        if self.config.log_prompts:
            logger.debug(f"System prompt:\n{self.system_prompt}")
    
    def _init_memory(self, memory: Optional[Memory] = None):
        """初始化 Memory 层"""
        logger.info("Initializing Memory layer...")
        
        if memory is not None:
            self.memory = memory
        else:
            memory_config = MemoryConfig(
                agent_id=self.config.engine_id,
                storage_path=self.config.memory_storage_path,
                short_term_capacity=self.config.short_term_capacity,
                rag_top_k=self.config.rag_top_k,
            )
            self.memory = Memory(config=memory_config)
        
        logger.info("Memory layer initialized")
    
    def _init_model_adapter(self, adapter: Optional[ModelAdapter] = None):
        """初始化 Model Adapter 层"""
        logger.info("Initializing Model Adapter layer...")
        
        if adapter is not None:
            self.model_adapter = adapter
        else:
            try:
                # 尝试使用现有配置创建 ModelAdapter
                model_cfg = ModelConfig()
                self.model_adapter = ModelAdapter(config=model_cfg)
            except Exception as e:
                logger.warning(f"Failed to initialize ModelAdapter: {e}")
                logger.warning("Using mock mode - responses will be simulated")
                self.model_adapter = None
        
        logger.info(f"Model adapter: {self.model_adapter.__class__.__name__ if self.model_adapter else 'None'}")
    
    def _init_conversation_manager(self):
        """初始化对话管理器"""
        self.conversation_manager = ConversationManager(
            engine_id=self.config.engine_id
        )
    
    # ========================
    # 核心对话方法
    # ========================
    
    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        use_memory: bool = True,
        use_rag: bool = True,
        **kwargs
    ) -> ChatResponse:
        """
        处理用户对话
        
        Args:
            message: 用户输入消息
            session_id: 会话ID（可选，不提供则创建新会话）
            user_id: 用户ID（可选）
            use_memory: 是否使用记忆
            use_rag: 是否使用RAG检索
            
        Returns:
            ChatResponse: 对话响应
        """
        start_time = time.time()
        message_id = str(uuid.uuid4())
        
        # 获取或创建会话
        session = self._get_or_create_session(session_id, user_id)
        session_id = session.id
        
        logger.info(f"[{session_id}] User: {message[:50]}...")
        
        try:
            # Step 1: 检索记忆上下文
            memory_context = ""
            if use_memory and self.config.memory_enabled:
                memory_context = self._get_memory_context(message, use_rag=use_rag)
            
            # Step 2: 构建消息列表
            messages = self._build_messages(message, memory_context, session)
            
            # Step 3: 调用 LLM
            response = self._call_llm(messages, **kwargs)
            
            # Step 4: 存储对话记忆
            if self.config.memory_enabled:
                self._store_conversation(session_id, message, response.content)
            
            # Step 5: 更新会话历史
            session.add_message("user", message)
            session.add_message("assistant", response.content)
            
            # 构建返回结果
            result = ChatResponse(
                content=response.content,
                session_id=session_id,
                message_id=message_id,
                model=response.model,
                provider=response.provider,
                usage=response.usage,
                latency_ms=(time.time() - start_time) * 1000,
                metadata={
                    "memory_used": use_memory and self.config.memory_enabled,
                    "rag_used": use_rag and self.config.memory_enabled,
                }
            )
            
            logger.info(f"[{session_id}] Assistant: {response.content[:50]}... ({result.latency_ms:.0f}ms)")
            
            return result
            
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            return ChatResponse(
                content=f"抱歉，发生了错误: {str(e)}",
                session_id=session_id,
                message_id=message_id,
                model="error",
                provider="error",
                metadata={"error": str(e)}
            )
    
    def _get_or_create_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Session:
        """获取或创建会话"""
        if session_id:
            session = self.conversation_manager.get_session(session_id)
            if session:
                return session
        
        return self.conversation_manager.create_session(user_id=user_id)
    
    def _get_memory_context(self, query: str, use_rag: bool = True) -> str:
        """获取记忆上下文"""
        contexts = []
        
        # 短期记忆 - 最近对话
        short_term = self.memory.get_short_term_context()
        if short_term:
            contexts.append(f"[近期对话]\n{short_term}")
        
        # RAG 检索 - 长期记忆
        if use_rag:
            rag_results = self.memory.retrieve(query)
            if rag_results.documents:
                docs_text = "\n".join([
                    f"- {doc.content[:200]}..." 
                    for doc in rag_results.documents[:self.config.rag_top_k]
                ])
                contexts.append(f"[相关记忆]\n{docs_text}")
        
        return "\n\n".join(contexts) if contexts else ""
    
    def _build_messages(
        self,
        user_message: str,
        memory_context: str,
        session: Session
    ) -> List[Message]:
        """构建消息列表"""
        messages = []
        
        # 系统消息
        system_content = self.system_prompt
        
        # 注入记忆上下文到系统提示
        if memory_context:
            system_content += f"\n\n## 上下文信息\n{memory_context}\n\n请结合以上上下文信息回答用户问题。"
        
        messages.append(Message(
            role=MessageRole.SYSTEM,
            content=system_content
        ))
        
        # 对话历史
        for msg in session.get_history():
            role = MessageRole.USER if msg["role"] == "user" else MessageRole.ASSISTANT
            messages.append(Message(
                role=role,
                content=msg["content"]
            ))
        
        # 当前用户消息
        messages.append(Message(
            role=MessageRole.USER,
            content=user_message
        ))
        
        if self.config.log_prompts:
            logger.debug("=== Messages ===")
            for i, msg in enumerate(messages):
                logger.debug(f"[{i}] {msg.role.value}: {msg.content[:100]}...")
        
        return messages
    
    def _call_llm(
        self,
        messages: List[Message],
        **kwargs
    ) -> ModelResponse:
        """调用 LLM"""
        if self.model_adapter is None:
            # Mock 模式 - 模拟响应
            return self._mock_response(messages)
        
        try:
            # 使用 ModelAdapter 的同步接口
            # 分离系统消息和用户消息
            system_prompt = None
            user_prompt = ""
            
            for msg in messages:
                if msg.role == MessageRole.SYSTEM:
                    system_prompt = msg.content
                elif msg.role == MessageRole.USER:
                    user_prompt = msg.content  # 使用最后一条用户消息
            
            # 调用 chat_sync
            response = self.model_adapter.chat_sync(
                prompt=user_prompt,
                system=system_prompt,
                model=self.config.model_name,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            )
            return response
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # 降级到 mock
            return self._mock_response(messages)
    
    def _mock_response(self, messages: List[Message]) -> ModelResponse:
        """模拟响应（当无法调用真实LLM时）"""
        # 提取用户消息
        user_msg = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                user_msg = msg.content
                break
        
        # 简单的模拟回复
        mock_replies = [
            f"这是一个模拟回复。你说：'{user_msg[:30]}...'",
            f"我理解你的意思。关于 '{user_msg[:20]}...' 这个问题...",
            f"感谢你的消息！我正在学习如何更好地回答 '{user_msg[:20]}...' 相关的问题。",
        ]
        
        import random
        content = random.choice(mock_replies)
        
        return ModelResponse(
            content=content,
            model=self.config.model_name,
            provider=self.config.model_provider,
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            latency_ms=100.0,
        )
    
    def _store_conversation(self, session_id: str, user_message: str, assistant_response: str):
        """存储对话到记忆"""
        try:
            # 添加到短期记忆
            self.memory.add_turn("user", user_message)
            self.memory.add_turn("assistant", assistant_response)
        except Exception as e:
            logger.warning(f"Failed to store conversation: {e}")
    
    # ========================
    # 会话管理方法
    # ========================
    
    def create_session(self, user_id: Optional[str] = None) -> Session:
        """创建新会话"""
        return self.conversation_manager.create_session(user_id=user_id)
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.conversation_manager.get_session(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        return self.conversation_manager.delete_session(session_id)
    
    def list_sessions(self, user_id: Optional[str] = None) -> List[Session]:
        """列出会话"""
        return self.conversation_manager.list_sessions(user_id=user_id)
    
    # ========================
    # 知识管理方法
    # ========================
    
    def add_knowledge(
        self,
        content: str,
        source: str = "manual",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        添加知识到长期记忆
        
        Args:
            content: 知识内容
            source: 来源标识
            metadata: 额外元数据
        """
        self.memory.add_long_term_memory(
            content=content,
            source=source,
            metadata=metadata or {}
        )
        logger.info(f"Knowledge added from {source}: {content[:50]}...")
    
    def search_knowledge(self, query: str, top_k: int = 5) -> List[str]:
        """
        搜索知识
        
        Args:
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            匹配的知识内容列表
        """
        results = self.memory.retrieve(query, top_k=top_k)
        return [doc.content for doc in results.documents]
    
    # ========================
    # 配置更新方法
    # ========================
    
    def update_soul(self, soul_config: Dict[str, Any]):
        """更新 Soul 配置"""
        self.soul_config = soul_config
        self._build_system_prompt()
        logger.info("Soul configuration updated")
    
    def update_system_prompt(self, prompt: str):
        """更新系统提示词（完全替换）"""
        self.config.system_prompt = prompt
        # 直接设置，不经过 _build_system_prompt 以避免 Soul 配置合并
        self.system_prompt = prompt
        logger.info("System prompt updated")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        return {
            "engine_id": self.config.engine_id,
            "engine_name": self.config.engine_name,
            "soul_name": self.soul_config.get("name", "Unknown"),
            "memory_stats": self.memory.get_stats(),
            "session_count": len(self.conversation_manager.sessions),
            "model": self.config.model_name,
            "provider": self.config.model_provider,
        }
    
    def reset(self):
        """重置引擎状态"""
        self.conversation_manager.clear_all_sessions()
        logger.info("Engine reset complete")
    
    def __repr__(self) -> str:
        return f"NeshamaEngine(id={self.config.engine_id}, soul={self.soul_config.get('name', 'Unknown')})"


# ============================================================
# 便捷函数
# ============================================================

_default_engine: Optional[NeshamaEngine] = None


def get_engine(config: Optional[EngineConfig] = None) -> NeshamaEngine:
    """获取默认引擎实例"""
    global _default_engine
    if _default_engine is None:
        _default_engine = NeshamaEngine(config=config)
    return _default_engine


def reset_engine():
    """重置默认引擎"""
    global _default_engine
    if _default_engine:
        _default_engine.reset()
    _default_engine = None


# ============================================================
# 使用示例（可直接运行测试）
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Neshama Engine Demo")
    print("=" * 50)
    
    # 创建引擎
    engine = NeshamaEngine()
    print(f"\n引擎信息: {engine}")
    print(f"系统提示词预览:\n{engine.system_prompt[:200]}...\n")
    
    # 基础对话
    print("\n--- 对话测试 ---")
    response = engine.chat("你好，请介绍一下你自己")
    print(f"用户: 你好，请介绍一下你自己")
    print(f"助手: {response.content}")
    
    # 多轮对话
    print("\n--- 多轮对话测试 ---")
    session = engine.create_session(user_id="demo_user")
    print(f"创建会话: {session.id}")
    
    response1 = engine.chat("我想学习Python", session_id=session.id)
    print(f"用户: 我想学习Python")
    print(f"助手: {response1.content[:100]}...")
    
    response2 = engine.chat("有什么推荐的学习资源吗？", session_id=session.id)
    print(f"用户: 有什么推荐的学习资源吗？")
    print(f"助手: {response2.content[:100]}...")
    
    # 添加知识测试
    print("\n--- 知识库测试 ---")
    engine.add_knowledge(
        "Python的创始人是Guido van Rossum，1991年发布第一个版本。",
        source="python_history"
    )
    results = engine.search_knowledge("Python创始人")
    print(f"搜索'Python创始人'结果: {results}")
    
    # 统计信息
    print("\n--- 统计信息 ---")
    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 50)
    print("Demo Complete!")
    print("=" * 50)

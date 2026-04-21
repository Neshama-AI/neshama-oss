"""
Neshama Core - 核心引擎测试
============================

测试 NeshamaEngine 和 ConversationManager 的基本功能。

运行方式：
    python -m pytest Neshama/tests/test_engine.py -v
    # 或
    python Neshama/tests/test_engine.py
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

# 添加项目根目录到路径
import sys
import os
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_parent_dir = os.path.dirname(_project_root)  # 获取父目录（/app/data/所有对话/主对话）
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from Neshama.core import (
    NeshamaEngine,
    EngineConfig,
    ChatResponse,
    ConversationManager,
    Session,
    Message
)


class TestConversationManager(unittest.TestCase):
    """测试 ConversationManager"""
    
    def setUp(self):
        """测试初始化"""
        self.manager = ConversationManager(
            engine_id="test_engine",
            max_sessions=10,
            session_timeout_minutes=5
        )
    
    def test_create_session(self):
        """测试创建会话"""
        session = self.manager.create_session(user_id="test_user")
        
        self.assertIsNotNone(session)
        self.assertEqual(session.user_id, "test_user")
        self.assertEqual(len(session.messages), 0)
    
    def test_get_session(self):
        """测试获取会话"""
        session = self.manager.create_session(user_id="test_user")
        session_id = session.id
        
        retrieved = self.manager.get_session(session_id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, session_id)
        self.assertEqual(retrieved.user_id, "test_user")
    
    def test_get_nonexistent_session(self):
        """测试获取不存在的会话"""
        result = self.manager.get_session("nonexistent_id")
        self.assertIsNone(result)
    
    def test_delete_session(self):
        """测试删除会话"""
        session = self.manager.create_session(user_id="test_user")
        session_id = session.id
        
        result = self.manager.delete_session(session_id)
        
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_session(session_id))
    
    def test_add_message(self):
        """测试添加消息"""
        session = self.manager.create_session()
        
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")
        
        self.assertEqual(len(session.messages), 2)
        self.assertEqual(session.messages[0].content, "Hello")
        self.assertEqual(session.messages[1].content, "Hi there!")
    
    def test_get_history(self):
        """测试获取历史"""
        session = self.manager.create_session()
        
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        session.add_message("user", "How are you?")
        
        history = session.get_history()
        
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Hello")
    
    def test_get_history_with_limit(self):
        """测试限制历史条数"""
        session = self.manager.create_session()
        
        for i in range(5):
            session.add_message("user", f"Message {i}")
        
        history = session.get_history(limit=2)
        
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]["content"], "Message 4")
    
    def test_session_expiry(self):
        """测试会话过期"""
        # 创建超短超时的会话
        session = Session(
            id="test",
            timeout_minutes=0  # 立即过期
        )
        
        # 等待一小段时间
        import time
        time.sleep(0.1)
        
        self.assertTrue(session.is_expired())
    
    def test_list_sessions_by_user(self):
        """测试按用户列出会话"""
        self.manager.create_session(user_id="user1")
        self.manager.create_session(user_id="user1")
        self.manager.create_session(user_id="user2")
        
        sessions = self.manager.list_sessions(user_id="user1")
        
        self.assertEqual(len(sessions), 2)
        for session in sessions:
            self.assertEqual(session.user_id, "user1")
    
    def test_clear_history(self):
        """测试清空历史"""
        session = self.manager.create_session()
        
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        
        session.clear_history()
        
        self.assertEqual(len(session.messages), 0)


class TestSession(unittest.TestCase):
    """测试 Session 类"""
    
    def test_create_session(self):
        """测试创建会话"""
        session = Session(user_id="test")
        
        self.assertIsNotNone(session.id)
        self.assertEqual(session.user_id, "test")
        self.assertIsNotNone(session.created_at)
    
    def test_custom_session_id(self):
        """测试自定义会话ID"""
        custom_id = "my_custom_id"
        session = Session(id=custom_id)
        
        self.assertEqual(session.id, custom_id)
    
    def test_touch(self):
        """测试更新时间戳"""
        session = Session()
        original_update = session.updated_at
        
        import time
        time.sleep(0.01)
        
        session.touch()
        
        self.assertGreater(session.updated_at, original_update)
    
    def test_max_history_limit(self):
        """测试最大历史限制"""
        session = Session(max_history=3)
        
        for i in range(5):
            session.add_message("user", f"Message {i}")
        
        self.assertEqual(len(session.messages), 3)
        # 应该是最后3条
        self.assertEqual(session.messages[-1].content, "Message 4")
    
    def test_to_dict(self):
        """测试转换为字典"""
        session = Session(id="test_id", user_id="user1")
        session.add_message("user", "Hello")
        
        data = session.to_dict()
        
        self.assertEqual(data["id"], "test_id")
        self.assertEqual(data["user_id"], "user1")
        self.assertEqual(data["message_count"], 1)


class TestEngineConfig(unittest.TestCase):
    """测试 EngineConfig"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = EngineConfig()
        
        self.assertEqual(config.engine_id, "default")
        self.assertTrue(config.memory_enabled)
        self.assertTrue(config.soul_enabled)
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = EngineConfig(
            engine_id="my_engine",
            model_provider="openai",
            model_name="gpt-4",
            temperature=0.9
        )
        
        self.assertEqual(config.engine_id, "my_engine")
        self.assertEqual(config.model_provider, "openai")
        self.assertEqual(config.model_name, "gpt-4")
        self.assertEqual(config.temperature, 0.9)


class TestChatResponse(unittest.TestCase):
    """测试 ChatResponse"""
    
    def test_create_response(self):
        """测试创建响应"""
        response = ChatResponse(
            content="Hello!",
            session_id="session123",
            message_id="msg456",
            model="gpt-4",
            provider="openai"
        )
        
        self.assertEqual(response.content, "Hello!")
        self.assertEqual(response.session_id, "session123")
        self.assertEqual(response.latency_ms, 0.0)
    
    def test_to_dict(self):
        """测试转换为字典"""
        response = ChatResponse(
            content="Test",
            session_id="s1",
            message_id="m1",
            model="test",
            provider="test"
        )
        
        data = response.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertEqual(data["content"], "Test")
        self.assertIn("usage", data)
    
    def test_str_representation(self):
        """测试字符串表示"""
        response = ChatResponse(
            content="Hello World",
            session_id="s1",
            message_id="m1",
            model="test",
            provider="test"
        )
        
        self.assertEqual(str(response), "Hello World")


class TestNeshamaEngine(unittest.TestCase):
    """测试 NeshamaEngine"""
    
    def setUp(self):
        """测试初始化"""
        # 创建测试配置
        self.config = EngineConfig(
            engine_id="test_engine",
            debug=False,
            memory_enabled=True
        )
    
    @patch('Neshama.core.engine.ModelAdapter')
    def test_create_engine(self, mock_adapter):
        """测试创建引擎"""
        engine = NeshamaEngine(config=self.config)
        
        self.assertEqual(engine.config.engine_id, "test_engine")
        self.assertIsNotNone(engine.conversation_manager)
    
    @patch('Neshama.core.engine.ModelAdapter')
    def test_create_session(self, mock_adapter):
        """测试创建会话"""
        engine = NeshamaEngine(config=self.config)
        
        session = engine.create_session(user_id="test_user")
        
        self.assertIsNotNone(session)
        self.assertEqual(session.user_id, "test_user")
    
    @patch('Neshama.core.engine.ModelAdapter')
    def test_get_session(self, mock_adapter):
        """测试获取会话"""
        engine = NeshamaEngine(config=self.config)
        
        created = engine.create_session(user_id="test")
        retrieved = engine.get_session(created.id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, created.id)
    
    @patch('Neshama.core.engine.ModelAdapter')
    def test_update_system_prompt(self, mock_adapter):
        """测试更新系统提示词"""
        engine = NeshamaEngine(config=self.config)
        
        new_prompt = "You are a helpful assistant."
        engine.update_system_prompt(new_prompt)
        
        self.assertEqual(engine.system_prompt, new_prompt)
    
    @patch('Neshama.core.engine.ModelAdapter')
    def test_get_stats(self, mock_adapter):
        """测试获取统计信息"""
        engine = NeshamaEngine(config=self.config)
        
        stats = engine.get_stats()
        
        self.assertIn("engine_id", stats)
        self.assertIn("memory_stats", stats)
        self.assertEqual(stats["engine_id"], "test_engine")
    
    @patch('Neshama.core.engine.ModelAdapter')
    def test_reset(self, mock_adapter):
        """测试重置引擎"""
        engine = NeshamaEngine(config=self.config)
        
        engine.create_session()
        engine.reset()
        
        self.assertEqual(len(engine.conversation_manager.sessions), 0)


class TestMessage(unittest.TestCase):
    """测试 Message 类"""
    
    def test_create_message(self):
        """测试创建消息"""
        msg = Message(role="user", content="Hello")
        
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Hello")
        self.assertIsNotNone(msg.timestamp)
    
    def test_to_dict(self):
        """测试转换为字典"""
        msg = Message(role="assistant", content="Hi!")
        
        data = msg.to_dict()
        
        self.assertEqual(data["role"], "assistant")
        self.assertEqual(data["content"], "Hi!")
        self.assertIn("timestamp", data)
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "role": "user",
            "content": "Test",
            "timestamp": datetime.now().isoformat(),
            "metadata": {"key": "value"}
        }
        
        msg = Message.from_dict(data)
        
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Test")


# ============================================================
# 运行测试
# ============================================================

def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Neshama Core - 测试套件")
    print("=" * 60)
    print()
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestConversationManager))
    suite.addTests(loader.loadTestsFromTestCase(TestSession))
    suite.addTests(loader.loadTestsFromTestCase(TestEngineConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestChatResponse))
    suite.addTests(loader.loadTestsFromTestCase(TestNeshamaEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestMessage))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印结果
    print()
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"  运行: {result.testsRun}")
    print(f"  成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失败: {len(result.failures)}")
    print(f"  错误: {len(result.errors)}")
    print()
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

# Neshama Agent 贡献指南

感谢您对 Neshama Agent 开源项目的关注！我们欢迎各种形式的贡献。

## 如何贡献

### 报告问题

- 使用 GitHub Issues 报告 bug
- 提交功能请求
- 回答其他用户的问题

### 提交代码

1. **Fork 本仓库**
2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```
3. **编写代码** - 遵循项目的代码风格
4. **添加测试** - 确保新功能有测试覆盖
5. **提交更改**
   ```bash
   git commit -m "Add: 描述您的更改"
   ```
6. **推送到您的 Fork**
   ```bash
   git push origin feature/your-feature-name
   ```
7. **创建 Pull Request**

## 代码规范

### Python 代码风格

- 遵循 PEP 8
- 使用有意义的变量和函数命名
- 添加 docstrings
- 类型注解（可选但推荐）

```python
def process_message(message: str, user_id: int) -> dict:
    """
    处理用户消息
    
    Args:
        message: 用户输入的消息
        user_id: 用户ID
    
    Returns:
        处理结果字典
    """
    # ...
```

### Django 代码规范

- 使用 Django REST Framework 序列化器
- 遵循 Django 模型命名规范
- 添加适当的权限类
- 使用 CBV 或 FBV 保持一致

### 提交信息规范

使用以下格式：

```
<type>: <subject>

<body>
```

类型：
- `Add`: 新功能
- `Fix`: Bug 修复
- `Update`: 更新功能
- `Refactor`: 重构
- `Docs`: 文档更新
- `Test`: 测试相关
- `Chore`: 其他

示例：
```
Add: 添加 Soul 引擎情绪系统

- 实现情绪分类器
- 添加情绪状态管理
- 更新单元测试
```

## 模块贡献指南

### Soul 模块

- 在 `soul/modules/` 下添加新的系统模块
- 实现标准的接口
- 添加配置示例

### Memory 模块

- 遵循 3 层记忆架构
- 保持与 RAG 的兼容性
- 文档化配置参数

### Model Adapter

- 在 `model_adapter/providers/` 下添加新的模型支持
- 继承基础 Provider 类
- 实现标准接口方法

## 测试指南

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/soul/
pytest tests/memory/

# 生成覆盖率报告
pytest --cov=.
```

## 开发环境

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行代码检查
flake8 .
black .
mypy .

# 运行所有检查
make check
```

## 许可

通过贡献代码，您同意将您的代码以 MIT 许可证开源。

## 行为准则

请尊重其他贡献者，保持友善和专业的态度。

## 联系方式

- GitHub Issues: https://github.com/neshama-ai/neshama-oss/issues
- 讨论群: https://github.com/neshama-ai/neshama-oss/discussions

感谢您的贡献！

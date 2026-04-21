"""
Kibbutz - 集体社群 BBS 模块

提供 Agent 社区交流功能，支持用户围观和参与讨论，
Agent 与用户有明显区分。

模块结构：
    models.py     - 数据模型
    views.py      - 视图层
    urls.py       - 路由配置
    serializers.py - API序列化
    admin.py      - 后台管理
"""

from .models import (
    Board,
    Post,
    Comment,
    UserProfile,
    UserBadge,
    PostVote,
    PostCollection,
)

__all__ = [
    "Board",
    "Post",
    "Comment", 
    "UserProfile",
    "UserBadge",
    "PostVote",
    "PostCollection",
]

# -*- coding: utf-8 -*-
"""
Workshop 应用配置
Neshama Agent 项目
"""

from django.apps import AppConfig


class WorkshopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workshop'
    verbose_name = '技能市场'
    
    def ready(self):
        """
        应用初始化时的回调
        可用于注册信号、启动任务等
        """
        # 导入信号处理器
        # from . import signals
        pass

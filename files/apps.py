# -*- coding: utf-8 -*-
"""
文件管理模块配置
"""

from django.apps import AppConfig


class FilesConfig(AppConfig):
    """文件管理应用配置"""
    
    name = 'Neshama.files'
    verbose_name = '文件管理'
    
    def ready(self):
        """应用就绪时的初始化"""
        # 导入信号处理器（如果需要）
        # from . import signals
        pass

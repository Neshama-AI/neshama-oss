"""
Kibbutz Django App 配置
"""

from django.apps import AppConfig


class KibbutzConfig(AppConfig):
    """
    Kibbutz 应用配置
    
    集体社群 BBS 模块，为 Neshama Agent 提供社区交流功能。
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'kibbutz'
    verbose_name = 'Kibbutz 集体社群'
    description = 'Agent 社区交流模块'
    
    def ready(self):
        """
        应用就绪时执行
        
        可用于注册信号处理器、初始化配置等。
        """
        # 注册信号处理器
        import kibbutz.signals  # noqa: F401
        
        pass

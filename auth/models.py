"""
Neshama Agent 用户认证系统模型 - 开源版
基础认证模块，不包含商业OAuth功能（微信/支付宝）
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class UserProfile(AbstractUser):
    """
    用户模型扩展（开源版）
    - 继承Django默认User的所有字段
    - 保留基础用户信息字段
    - 不包含OAuth商业功能
    """
    
    class UserType(models.TextChoices):
        FREE = 'free', '免费用户'
        PRO = 'pro', 'Pro用户'
    
    class Gender(models.TextChoices):
        UNKNOWN = 'unknown', '未知'
        MALE = 'male', '男'
        FEMALE = 'female', '女'
    
    # ============ 用户信息 ============
    avatar_url = models.URLField(
        max_length=500, blank=True,
        verbose_name='头像URL'
    )
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        default=Gender.UNKNOWN,
        verbose_name='性别'
    )
    birthday = models.DateField(
        null=True, blank=True,
        verbose_name='生日'
    )
    bio = models.TextField(
        max_length=500, blank=True,
        verbose_name='个人简介'
    )
    
    # ============ 邀请系统 ============
    invite_code = models.CharField(
        max_length=20, unique=True,
        verbose_name='个人邀请码',
        db_index=True
    )
    invited_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invited_users',
        verbose_name='邀请人'
    )
    
    # ============ 安全相关 ============
    email_verified = models.BooleanField(
        default=False,
        verbose_name='邮箱已验证'
    )
    last_login_ip = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name='最后登录IP'
    )
    
    # ============ 统计字段 ============
    total_login_count = models.PositiveIntegerField(
        default=0,
        verbose_name='登录次数'
    )
    
    class Meta:
        db_table = 'auth_user_profile'
        verbose_name = '用户'
        verbose_name_plural = '用户'
        indexes = [
            models.Index(fields=['invite_code']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    def generate_invite_code(self) -> str:
        """生成唯一邀请码"""
        import secrets
        import string
        if not self.invite_code:
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) 
                          for _ in range(8))
            # 确保唯一
            while UserProfile.objects.filter(invite_code=code).exists():
                code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) 
                              for _ in range(8))
            self.invite_code = code
            self.save(update_fields=['invite_code'])
        return self.invite_code


class LoginLog(models.Model):
    """
    登录日志
    """
    class LoginType(models.TextChoices):
        PASSWORD = 'password', '密码登录'
        SMS = 'sms', '短信验证码登录'
        REFRESH = 'refresh', 'Token刷新'
    
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='login_logs'
    )
    login_type = models.CharField(
        max_length=20,
        choices=LoginType.choices,
        verbose_name='登录方式'
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name='IP地址'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='User-Agent'
    )
    login_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name='登录时间'
    )
    success = models.BooleanField(
        default=True,
        verbose_name='是否成功'
    )
    
    class Meta:
        db_table = 'auth_login_log'
        verbose_name = '登录日志'
        verbose_name_plural = '登录日志'
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', '-login_time']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.get_login_type_display()} @ {self.login_time}"

"""
Neshama Agent 用户认证后台管理 - 开源版
基础用户管理，不包含OAuth和Pro会员功能
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserProfile, LoginLog


@admin.register(UserProfile)
class UserProfileAdmin(BaseUserAdmin):
    """用户资料管理"""
    
    list_display = ['username', 'email', 'avatar_url', 'gender', 'invited_by', 'total_login_count', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'email_verified', 'date_joined']
    search_fields = ['username', 'email']
    ordering = ['-date_joined']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('用户信息', {
            'fields': ('avatar_url', 'gender', 'birthday', 'bio')
        }),
        ('邀请系统', {
            'fields': ('invite_code', 'invited_by')
        }),
        ('安全', {
            'fields': ('email_verified', 'last_login_ip')
        }),
    )
    
    readonly_fields = ['invite_code', 'date_joined', 'last_login']


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    """登录日志管理"""
    
    list_display = ['user', 'login_type_display', 'ip_address', 'login_time', 'success']
    list_filter = ['login_type', 'success', 'login_time']
    search_fields = ['user__username', 'user__email', 'ip_address']
    ordering = ['-login_time']
    date_hierarchy = 'login_time'
    
    readonly_fields = ['user', 'login_type', 'ip_address', 'user_agent', 'login_time', 'success']
    
    def login_type_display(self, obj):
        return obj.get_login_type_display()
    login_type_display.short_description = '登录方式'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

"""
Neshama Agent 序列化器 - 开源版
用户注册/登录/资料相关序列化
不包含商业OAuth功能
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile, LoginLog


class UserRegisterSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='密码（至少8位）'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='确认密码'
    )
    invite_code = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='邀请码（可选）'
    )
    
    class Meta:
        model = UserProfile
        fields = ['username', 'email', 'password', 'password_confirm', 'invite_code']
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True},
        }
    
    def validate_username(self, value):
        """验证用户名"""
        value = value.strip().lower()
        if len(value) < 3:
            raise serializers.ValidationError('用户名至少3个字符')
        if not value.isalnum():
            raise serializers.ValidationError('用户名只能包含字母和数字')
        return value
    
    def validate_email(self, value):
        """验证邮箱唯一性"""
        value = value.strip().lower()
        if UserProfile.objects.filter(email=value).exists():
            raise serializers.ValidationError('该邮箱已被注册')
        return value
    
    def validate(self, attrs):
        """验证两次密码一致"""
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': '两次密码不一致'})
        return attrs
    
    def create(self, validated_data):
        """创建用户"""
        invite_code = validated_data.pop('invite_code', None)
        
        # 检查邀请码
        inviter = None
        if invite_code:
            try:
                inviter = UserProfile.objects.get(invite_code=invite_code)
            except UserProfile.DoesNotExist:
                pass
        
        # 创建用户
        user = UserProfile.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            invited_by=inviter
        )
        
        # 生成邀请码
        user.generate_invite_code()
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """用户登录序列化器"""
    
    login_type = serializers.ChoiceField(
        choices=['email'],
        default='email',
        help_text='登录方式'
    )
    email = serializers.EmailField(
        required=True,
        help_text='邮箱'
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text='密码'
    )


class UserProfileSerializer(serializers.ModelSerializer):
    """用户资料序列化器"""
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'username', 'email', 'avatar_url', 'gender',
            'bio', 'invite_code', 'total_login_count', 'date_joined',
            'last_login'
        ]
        read_only_fields = ['id', 'username', 'email', 'invite_code', 
                           'total_login_count', 'date_joined', 'last_login']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """用户资料更新序列化器"""
    
    class Meta:
        model = UserProfile
        fields = ['avatar_url', 'gender', 'birthday', 'bio']


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码序列化器"""
    
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text='旧密码'
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='新密码'
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text='确认新密码'
    )
    
    def validate_old_password(self, value):
        """验证旧密码"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('旧密码不正确')
        return value
    
    def validate(self, attrs):
        """验证新密码一致"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': '两次密码不一致'})
        return attrs
    
    def validate_new_password(self, value):
        """验证新密码强度"""
        try:
            validate_password(value)
        except Exception as e:
            raise serializers.ValidationError(list(e))
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    """密码重置请求序列化器"""
    
    email = serializers.EmailField(
        required=True,
        help_text='注册邮箱'
    )
    
    def validate_email(self, value):
        """验证邮箱存在"""
        value = value.strip().lower()
        if not UserProfile.objects.filter(email=value).exists():
            raise serializers.ValidationError('该邮箱未注册')
        return value


class LoginLogSerializer(serializers.ModelSerializer):
    """登录日志序列化器"""
    
    class Meta:
        model = LoginLog
        fields = ['id', 'login_type', 'ip_address', 'user_agent', 'login_time', 'success']
        read_only_fields = ['id', 'login_type', 'ip_address', 'user_agent', 'login_time', 'success']

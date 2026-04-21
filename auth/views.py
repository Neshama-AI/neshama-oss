"""
Neshama Agent 用户认证视图 - 开源版
支持邮箱注册登录、JWT认证
不包含商业OAuth功能（微信/支付宝）
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.utils import timezone

from .models import UserProfile, LoginLog
from .serializers import (
    UserRegisterSerializer, UserLoginSerializer, UserProfileSerializer,
    UserProfileUpdateSerializer, ChangePasswordSerializer,
    PasswordResetRequestSerializer, LoginLogSerializer,
)
from .permissions import IsOwnerOrReadOnly

User = get_user_model()


class RegisterView(APIView):
    """用户注册"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # 生成JWT
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': '注册成功',
                'user': UserProfileSerializer(user).data,
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'expires_in': 86400 * 7  # 7天
            }, status=status.HTTP_201_CREATED)
        
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """用户登录"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        login_type = data.get('login_type')
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        try:
            if login_type == 'email':
                user = authenticate(
                    username=data['email'].lower(),
                    password=data['password']
                )
            else:
                return Response({'error': '不支持的登录方式'}, status=status.HTTP_400_BAD_REQUEST)
            
            if user is None:
                self._log_login(None, login_type, ip_address, user_agent, False, '认证失败')
                return Response({'error': '认证失败'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # 更新登录统计
            user.last_login_ip = ip_address
            user.total_login_count += 1
            user.save(update_fields=['last_login_ip', 'total_login_count', 'last_login'])
            
            # 生成JWT
            refresh = RefreshToken.for_user(user)
            
            # 记录登录日志
            self._log_login(user, login_type, ip_address, user_agent, True)
            
            return Response({
                'message': '登录成功',
                'user': UserProfileSerializer(user).data,
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'expires_in': 86400 * 7  # 7天
            })
            
        except Exception as e:
            self._log_login(None, login_type, ip_address, user_agent, False, str(e))
            return Response({'error': f'登录失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def _log_login(self, user, login_type, ip_address, user_agent, success, reason=''):
        try:
            if user:
                LoginLog.objects.create(
                    user=user,
                    login_type=login_type,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=success
                )
        except Exception:
            pass


class UserProfileViewSet(viewsets.ModelViewSet):
    """用户资料管理"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer
    
    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """获取/更新当前用户资料"""
        if request.method == 'GET':
            serializer = UserProfileSerializer(request.user)
            return Response(serializer.data)
        else:
            serializer = UserProfileUpdateSerializer(
                request.user, 
                data=request.data, 
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(UserProfileSerializer(request.user).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """修改密码"""
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({'message': '密码修改成功'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def reset_password_request(self, request):
        """请求密码重置"""
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            # TODO: 发送重置邮件
            return Response({'message': '密码重置链接已发送到邮箱'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginLogViewSet(viewsets.ReadOnlyModelViewSet):
    """登录日志"""
    serializer_class = LoginLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return LoginLog.objects.filter(user=self.request.user)


def jwt_login(request):
    """
    JWT Token 获取
    用于第三方系统集成
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
            })
        return Response({'error': '认证失败'}, status=401)
    
    return Response({'error': '仅支持POST请求'}, status=405)

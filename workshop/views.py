# -*- coding: utf-8 -*-
"""
Workshop 视图层
Neshama Agent 项目 - 技能市场业务逻辑
"""

from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg, F
from django.core.paginator import Paginator
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.pagination import PageNumberPagination

from .models import (
    Skill, SkillCategory, SkillVersion, CreatorProfile,
    Rating, InstallRecord, Favorite, ReviewRequest, SkillStatus
)
from .serializers import (
    SkillListSerializer, SkillDetailSerializer, SkillCreateSerializer,
    SkillCategorySerializer, SkillVersionSerializer, RatingSerializer,
    CreatorProfileSerializer, InstallRecordSerializer, ReviewRequestSerializer,
    ReviewActionSerializer, StatisticsSerializer
)
from .review import AutomatedReviewer, CraftsmanLevelChecker, QualityScoreCalculator
from .permissions import IsOwnerOrReadOnly, IsVerifiedCreator


class StandardPagination(PageNumberPagination):
    """标准分页器"""
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50


class SkillCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    技能分类视图集
    
    list: 获取分类列表
    retrieve: 获取分类详情
    """
    queryset = SkillCategory.objects.filter(is_active=True, parent__isnull=True)
    serializer_class = SkillCategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    pagination_class = None  # 分类不需要分页


class SkillViewSet(viewsets.ModelViewSet):
    """
    技能视图集
    
    list: 获取技能列表（支持筛选、搜索、排序）
    retrieve: 获取技能详情
    create: 创建新技能
    update: 更新技能
    destroy: 删除技能
    """
    queryset = Skill.objects.select_related('creator', 'creator__user', 'category')
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'short_description', 'tags']
    ordering_fields = ['created_at', 'install_count', 'avg_rating', 'updated_at']
    ordering = ['-created_at']
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SkillListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SkillCreateSerializer
        return SkillDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 根据动作过滤可见性
        if self.action == 'list':
            # 列表页只显示已通过审核的技能
            queryset = queryset.filter(status=SkillStatus.APPROVED)
            
            # 分类筛选
            category = self.request.query_params.get('category')
            if category:
                queryset = queryset.filter(category__slug=category)
            
            # 标签筛选
            tag = self.request.query_params.get('tag')
            if tag:
                queryset = queryset.filter(tags__contains=[tag])
            
            # 精选技能筛选
            featured = self.request.query_params.get('featured')
            if featured and featured.lower() == 'true':
                queryset = queryset.filter(is_featured=True)
            
            # 价格筛选
            is_premium = self.request.query_params.get('premium')
            if is_premium == 'true':
                queryset = queryset.filter(is_premium=True)
            elif is_premium == 'false':
                queryset = queryset.filter(is_premium=False)
            
            # 评分筛选
            min_rating = self.request.query_params.get('min_rating')
            if min_rating:
                queryset = queryset.filter(avg_rating__gte=float(min_rating))
            
            # 安装量筛选
            min_installs = self.request.query_params.get('min_installs')
            if min_installs:
                queryset = queryset.filter(install_count__gte=int(min_installs))
        else:
            # 非列表页，创作者可看自己的所有技能
            if self.request.user.is_authenticated:
                queryset = queryset.filter(
                    Q(status=SkillStatus.APPROVED) |
                    Q(creator__user=self.request.user) |
                    Q(creator__user__is_staff=True)
                )
            else:
                queryset = queryset.filter(status=SkillStatus.APPROVED)
        
        return queryset
    
    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated(), IsVerifiedCreator()]
        elif self.action in ['update', 'partial_update', 'destroy', 'submit_review']:
            return [IsAuthenticated()]
        elif self.action in ['approve', 'reject']:
            return [IsAdminUser()]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        skill = serializer.save(creator=self.request.user.craftsman_profile)
        # 创建第一个版本
        SkillVersion.objects.create(
            skill=skill,
            version=skill.version,
            changelog='初始版本',
            file_url='',
            status=SkillStatus.PENDING
        )
    
    @action(detail=True, methods=['post'])
    def submit_review(self, request, slug=None):
        """提交技能审核"""
        skill = self.get_object()
        
        # 检查权限
        if skill.creator.user != request.user:
            return Response(
                {'error': '只有技能创作者可以提交审核'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 检查状态
        if skill.status not in [SkillStatus.DRAFT, SkillStatus.REJECTED]:
            return Response(
                {'error': f'当前状态不允许提交审核: {skill.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 运行自动化审核
        reviewer = AutomatedReviewer(skill)
        result, review_items = reviewer.run_all_checks()
        
        # 保存审核结果
        skill.review_items_cache = [
            {'name': item.name, 'status': item.status.value, 'message': item.message}
            for item in review_items
        ]
        
        if result.value == 'pass':
            # 自动通过
            skill.approve(request.user)
            return Response({
                'status': 'approved',
                'message': '审核通过',
                'review_items': skill.review_items_cache
            })
        elif result.value == 'fail':
            # 自动拒绝
            fail_messages = [item.message for item in review_items if item.status.value == 'fail']
            skill.reject(request.user, '; '.join(fail_messages))
            return Response({
                'status': 'rejected',
                'message': '审核未通过',
                'review_items': skill.review_items_cache
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # 需人工审核
            skill.submit_for_review()
            return Response({
                'status': 'pending',
                'message': '已提交人工审核',
                'review_items': skill.review_items_cache
            })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, slug=None):
        """管理员审核通过"""
        skill = self.get_object()
        
        if skill.status != SkillStatus.PENDING:
            return Response(
                {'error': '只有待审核状态的技能可以审核'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        skill.approve(request.user)
        return Response({'status': 'approved', 'message': '审核通过'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, slug=None):
        """管理员审核拒绝"""
        skill = self.get_object()
        serializer = ReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reason = serializer.validated_data.get('reason', '不符合上架标准')
        skill.reject(request.user, reason)
        
        return Response({'status': 'rejected', 'message': '审核拒绝'})
    
    @action(detail=True, methods=['post'])
    def install(self, request, slug=None):
        """安装技能"""
        skill = self.get_object()
        
        if skill.status != SkillStatus.APPROVED:
            return Response(
                {'error': '只能安装已通过的技能'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否已安装
        install, created = InstallRecord.objects.get_or_create(
            user=request.user,
            skill=skill,
            defaults={'version': skill.version}
        )
        
        if not created:
            # 更新为活跃状态
            install.is_active = True
            install.version = skill.version
            install.save()
            return Response({'status': 'updated', 'message': '已更新安装'})
        
        # 增加安装数
        skill.install_count = F('install_count') + 1
        skill.save(update_fields=['install_count'])
        skill.refresh_from_db()
        
        return Response({'status': 'installed', 'message': '安装成功'})
    
    @action(detail=True, methods=['post'])
    def uninstall(self, request, slug=None):
        """卸载技能"""
        skill = self.get_object()
        
        try:
            install = InstallRecord.objects.get(user=request.user, skill=skill)
            install.is_active = False
            install.save()
            return Response({'status': 'uninstalled', 'message': '已卸载'})
        except InstallRecord.DoesNotExist:
            return Response(
                {'error': '未安装此技能'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def rate(self, request, slug=None):
        """评分"""
        skill = self.get_object()
        serializer = RatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 检查是否安装过
        is_verified = InstallRecord.objects.filter(
            user=request.user, skill=skill, is_active=True
        ).exists()
        
        rating, created = Rating.objects.update_or_create(
            user=request.user,
            skill=skill,
            defaults={
                'rating': serializer.validated_data['rating'],
                'comment': serializer.validated_data.get('comment', ''),
                'is_anonymous': serializer.validated_data.get('is_anonymous', False),
                'is_verified': is_verified
            }
        )
        
        # 更新创作者评分统计
        skill.creator.update_stats()
        skill.creator.check_level_up()
        
        return Response(
            RatingSerializer(rating).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def favorite(self, request, slug=None):
        """收藏/取消收藏"""
        skill = self.get_object()
        
        favorite, created = Favorite.objects.get_or_create(
            user=request.user, skill=skill
        )
        
        if not created:
            favorite.delete()
            return Response({'status': 'unfavorited', 'message': '已取消收藏'})
        
        return Response({'status': 'favorited', 'message': '已收藏'})
    
    @action(detail=True, methods=['get'])
    def quality(self, request, slug=None):
        """获取技能质量评分详情"""
        skill = self.get_object()
        quality_info = QualityScoreCalculator.calculate(skill)
        return Response(quality_info)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """获取精选技能"""
        queryset = self.get_queryset().filter(is_featured=True)[:6]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """获取热门技能"""
        queryset = self.get_queryset().order_by('-install_count')[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recommended(self, request):
        """获取推荐技能（基于用户历史）"""
        user = request.user
        if not user.is_authenticated:
            # 未登录用户返回综合推荐
            queryset = self.get_queryset().order_by('-avg_rating', '-install_count')[:10]
        else:
            # TODO: 基于用户偏好推荐
            queryset = self.get_queryset().order_by('-avg_rating', '-install_count')[:10]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CreatorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    创作者视图集
    
    list: 获取创作者列表
    retrieve: 获取创作者详情
    me: 获取当前用户创作者资料
    stats: 获取当前用户等级统计
    """
    queryset = CreatorProfile.objects.all()
    serializer_class = CreatorProfileSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__username', 'title', 'bio']
    ordering_fields = ['skills_count', 'total_installs', 'avg_rating']
    ordering = ['-avg_rating']
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """获取当前用户创作者资料"""
        profile, created = CreatorProfile.objects.get_or_create(
            user=request.user,
            defaults={'level': 'novice'}
        )
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get', 'put'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        """编辑当前用户创作者资料"""
        profile, created = CreatorProfile.objects.get_or_create(
            user=request.user,
            defaults={'level': 'novice'}
        )
        
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def stats(self, request):
        """获取当前用户等级提升统计"""
        profile, _ = CreatorProfile.objects.get_or_create(
            user=request.user,
            defaults={'level': 'novice'}
        )
        stats = CraftsmanLevelChecker.evaluate(profile)
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def skills(self, request, pk=None):
        """获取创作者的技能列表"""
        creator = self.get_object()
        skills = Skill.objects.filter(
            creator=creator,
            status=SkillStatus.APPROVED
        )
        
        page = self.paginate_queryset(skills)
        if page is not None:
            serializer = SkillListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SkillListSerializer(skills, many=True)
        return Response(serializer.data)


class RatingViewSet(viewsets.ModelViewSet):
    """
    评分视图集
    """
    queryset = Rating.objects.select_related('skill', 'user')
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'rating', 'helpful_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 技能筛选
        skill_slug = self.request.query_params.get('skill')
        if skill_slug:
            queryset = queryset.filter(skill__slug=skill_slug)
        
        # 隐藏匿名评分（除非是本人）
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(is_anonymous=False) | Q(user=self.request.user)
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def helpful(self, request, pk=None):
        """标记评价为有帮助"""
        rating = self.get_object()
        
        # 不能给自己评分点赞
        if rating.user == request.user:
            return Response(
                {'error': '不能给自己的评价点赞'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: 记录点赞历史，防止重复点赞
        rating.helpful_count += 1
        rating.save(update_fields=['helpful_count'])
        
        return Response({'helpful_count': rating.helpful_count})


class InstallRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    安装记录视图集
    """
    queryset = InstallRecord.objects.select_related('skill', 'user')
    serializer_class = InstallRecordSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def installed_skills(self, request):
        """获取当前用户已安装的技能"""
        records = self.get_queryset().filter(is_active=True)
        skills = [record.skill for record in records]
        serializer = SkillListSerializer(skills, many=True)
        return Response(serializer.data)


class ReviewQueueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    审核队列视图集（管理员用）
    """
    queryset = ReviewRequest.objects.select_related(
        'skill', 'skill__creator', 'skill__creator__user', 'reviewer'
    ).filter(skill__status=SkillStatus.PENDING)
    serializer_class = ReviewRequestSerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['created_at']
    
    @action(detail=True, methods=['post'])
    def claim(self, request, pk=None):
        """认领审核任务"""
        review_request = self.get_object()
        
        if review_request.reviewer:
            return Response(
                {'error': '该任务已被认领'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        review_request.reviewer = request.user
        review_request.save()
        
        return Response({'status': 'claimed', 'message': '已认领任务'})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取审核统计"""
        pending = Skill.objects.filter(status=SkillStatus.PENDING).count()
        approved_today = Skill.objects.filter(
            status=SkillStatus.APPROVED,
            reviewed_at__date=timezone.now().date()
        ).count()
        rejected_today = Skill.objects.filter(
            status=SkillStatus.REJECTED,
            reviewed_at__date=timezone.now().date()
        ).count()
        
        return Response({
            'pending': pending,
            'approved_today': approved_today,
            'rejected_today': rejected_today
        })

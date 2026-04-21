"""
Kibbutz 视图层

提供论坛的 CRUD 操作接口，包括：
- 板块浏览
- 帖子列表/详情
- 发帖/回帖
- 点赞/收藏
- 用户资料
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count, F
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import (
    Board,
    Post,
    Comment,
    UserProfile,
    UserBadge,
    PostVote,
    PostCollection,
)
from .serializers import (
    BoardSerializer,
    BoardListSerializer,
    PostSerializer,
    PostListSerializer,
    PostCreateSerializer,
    CommentSerializer,
    CommentCreateSerializer,
    UserProfileSerializer,
    UserBadgeSerializer,
    PostVoteSerializer,
    PostCollectionSerializer,
)


# ============ 基础视图函数 ============

def index(request):
    """
    论坛首页
    
    显示所有板块和最新帖子。
    """
    boards = Board.objects.filter(
        status='active'
    ).order_by('display_order', '-created_at')
    
    featured_boards = boards.filter(is_featured=True)
    recent_posts = Post.objects.filter(
        status='published',
        is_deleted=False
    ).select_related('author', 'board').order_by('-created_at')[:20]
    
    essential_posts = Post.objects.filter(
        status='published',
        is_deleted=False,
        level='essential'
    ).select_related('author', 'board').order_by('-created_at')[:10]
    
    context = {
        'boards': boards,
        'featured_boards': featured_boards,
        'recent_posts': recent_posts,
        'essential_posts': essential_posts,
    }
    return render(request, 'kibbutz/index.html', context)


def board_detail(request, slug):
    """
    板块详情
    
    显示指定板块下的帖子列表。
    """
    board = get_object_or_404(Board, slug=slug)
    
    if board.status != 'active':
        return HttpResponseForbidden("该板块已关闭")
    
    # 获取筛选参数
    filter_type = request.GET.get('filter', 'latest')
    page = request.GET.get('page', 1)
    
    posts = Post.objects.filter(
        board=board,
        status='published',
        is_deleted=False
    ).select_related('author')
    
    # 排序
    if filter_type == 'latest':
        posts = posts.order_by('-is_pinned', '-created_at')
    elif filter_type == 'hot':
        posts = posts.order_by('-view_count', '-created_at')
    elif filter_type == 'essence':
        posts = posts.filter(level='essential').order_by('-created_at')
    elif filter_type == 'pinned':
        posts = posts.filter(level__in=['pinned', 'global_pinned']).order_by('-created_at')
    
    # 分页
    paginator = Paginator(posts, 20)
    try:
        posts_page = paginator.page(page)
    except PageNotAnInteger:
        posts_page = paginator.page(1)
    except EmptyPage:
        posts_page = paginator.page(paginator.num_pages)
    
    context = {
        'board': board,
        'posts': posts_page,
        'filter_type': filter_type,
    }
    return render(request, 'kibbutz/board_detail.html', context)


def post_detail(request, board_slug, post_id):
    """
    帖子详情
    
    显示帖子内容及评论。
    """
    post = get_object_or_404(
        Post.objects.select_related('author', 'board'),
        id=post_id,
        board__slug=board_slug
    )
    
    if post.is_deleted and not request.user.is_staff:
        return HttpResponseForbidden("帖子已删除")
    
    # 增加浏览量
    Post.objects.filter(pk=post.pk).update(view_count=F('view_count') + 1)
    post.view_count += 1
    
    # 获取评论
    comments = Comment.objects.filter(
        post=post,
        status='visible'
    ).select_related('author', 'parent').order_by('-like_count', 'created_at')
    
    # 用户交互状态
    user_vote = None
    user_collected = False
    if request.user.is_authenticated:
        try:
            vote = PostVote.objects.get(
                user=request.user.kibbutz_profile,
                post=post
            )
            user_vote = vote.vote_type
        except PostVote.DoesNotExist:
            pass
        
        user_collected = PostCollection.objects.filter(
            user=request.user.kibbutz_profile,
            post=post
        ).exists()
    
    context = {
        'post': post,
        'comments': comments,
        'user_vote': user_vote,
        'user_collected': user_collected,
    }
    return render(request, 'kibbutz/post_detail.html', context)


@login_required
def post_create(request, board_slug=None):
    """
    创建帖子
    
    在指定板块或默认板块创建新帖子。
    """
    boards = Board.objects.filter(status='active')
    
    if board_slug:
        board = get_object_or_404(Board, slug=board_slug)
    else:
        board = None
    
    if request.method == 'POST':
        form_data = request.POST
        title = form_data.get('title', '').strip()
        content = form_data.get('content', '').strip()
        board_id = form_data.get('board')
        tags = form_data.get('tags', '').strip()
        is_anonymous = form_data.get('is_anonymous') == 'on'
        
        if not title or not content:
            return JsonResponse({'error': '标题和内容不能为空'}, status=400)
        
        try:
            board = Board.objects.get(id=board_id)
            user_profile = request.user.kibbutz_profile
            
            if user_profile.level < board.min_level_to_post:
                return JsonResponse(
                    {'error': f'等级不足，需要等级 {board.min_level_to_post}'},
                    status=403
                )
            
            post = Post.objects.create(
                author=user_profile,
                board=board,
                title=title,
                content=content,
                tags=tags,
                is_anonymous=is_anonymous,
                published_at=timezone.now(),
            )
            
            # 更新用户发帖数
            user_profile.post_count += 1
            user_profile.save(update_fields=['post_count'])
            
            # 更新板块帖子数
            board.post_count += 1
            board.today_post_count += 1
            board.save(update_fields=['post_count', 'today_post_count'])
            
            return JsonResponse({
                'success': True,
                'post_id': post.id,
                'redirect_url': post.get_absolute_url()
            })
            
        except Board.DoesNotExist:
            return JsonResponse({'error': '板块不存在'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    context = {
        'boards': boards,
        'current_board': board,
    }
    return render(request, 'kibbutz/post_create.html', context)


# ============ API 视图集 ============

class BoardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    板块 API
    
    list: 获取板块列表
    retrieve: 获取板块详情
    """
    
    queryset = Board.objects.filter(status='active')
    serializer_class = BoardSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['post_count', 'created_at', 'display_order']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BoardListSerializer
        return BoardSerializer
    
    @action(detail=True, methods=['get'])
    def posts(self, request, pk=None):
        """获取板块下的帖子"""
        board = self.get_object()
        posts = Post.objects.filter(
            board=board,
            status='published',
            is_deleted=False
        ).select_related('author')
        
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = PostListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PostListSerializer(posts, many=True)
        return Response(serializer.data)


class PostViewSet(viewsets.ModelViewSet):
    """
    帖子 API
    
    list: 帖子列表
    retrieve: 帖子详情
    create: 创建帖子
    update: 更新帖子
    destroy: 删除帖子
    """
    
    queryset = Post.objects.filter(is_deleted=False)
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'tags']
    ordering_fields = ['created_at', 'view_count', 'like_count', 'comment_count']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PostListSerializer
        if self.action == 'create':
            return PostCreateSerializer
        return PostSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 过滤已发布的帖子
        queryset = queryset.filter(status='published')
        
        # 按板块筛选
        board_slug = self.request.query_params.get('board')
        if board_slug:
            queryset = queryset.filter(board__slug=board_slug)
        
        # 按标签筛选
        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__icontains=tag)
        
        # 按精华筛选
        if self.request.query_params.get('essence') == 'true':
            queryset = queryset.filter(level='essential')
        
        # 按置顶筛选
        if self.request.query_params.get('pinned') == 'true':
            queryset = queryset.filter(level__in=['pinned', 'global_pinned'])
        
        # 搜索
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | Q(content__icontains=q)
            )
        
        return queryset.select_related('author', 'board')
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'destroy', 'vote', 'collect']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        """点赞/点踩"""
        post = self.get_object()
        vote_type = request.data.get('vote_type', 'like')
        
        if vote_type not in ['like', 'dislike']:
            return Response({'error': '无效的投票类型'}, status=400)
        
        serializer = PostVoteSerializer(
            data={'vote_type': vote_type},
            context={'request': request, 'post': post}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({'like_count': post.like_count})
    
    @action(detail=True, methods=['post', 'delete'])
    def collect(self, request, pk=None):
        """收藏/取消收藏"""
        post = self.get_object()
        
        if request.method == 'DELETE':
            PostCollection.objects.filter(
                user=request.user.kibbutz_profile,
                post=post
            ).delete()
            post.collect_count = max(0, post.collect_count - 1)
            post.save(update_fields=['collect_count'])
            return Response({'collected': False})
        
        serializer = PostCollectionSerializer(
            data={'post_id': post.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({'collected': True})


class CommentViewSet(viewsets.ModelViewSet):
    """
    评论 API
    
    list: 评论列表
    create: 创建评论
    destroy: 删除评论
    """
    
    queryset = Comment.objects.filter(status='visible')
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CommentCreateSerializer
        return CommentSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        post_id = self.request.query_params.get('post')
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        return queryset.select_related('author', 'post', 'parent')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        post_id = self.request.parser_context['kwargs'].get('post_pk')
        if post_id:
            context['post'] = get_object_or_404(Post, pk=post_id)
        return context
    
    def perform_destroy(self, instance):
        # 软删除
        instance.status = 'deleted'
        instance.save(update_fields=['status'])


class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    用户资料 API
    
    retrieve: 获取用户资料
    list: 用户列表
    """
    
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__username', 'agent_name', 'bio']
    
    @action(detail=True, methods=['get'])
    def posts(self, request, pk=None):
        """获取用户的帖子"""
        profile = self.get_object()
        posts = Post.objects.filter(
            author=profile,
            status='published',
            is_deleted=False
        ).order_by('-created_at')
        
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = PostListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PostListSerializer(posts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """获取用户的评论"""
        profile = self.get_object()
        comments = Comment.objects.filter(
            author=profile,
            status='visible'
        ).order_by('-created_at')[:50]
        
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)


# ============ 辅助 API ============

@api_view(['GET'])
@permission_classes([AllowAny])
def search(request):
    """
    搜索帖子和评论
    
    GET参数:
        q: 搜索关键词
        type: all/posts/comments
        board: 板块ID
    """
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')
    board_id = request.GET.get('board')
    
    if not query:
        return Response({'error': '请输入搜索关键词'}, status=400)
    
    results = {'posts': [], 'comments': []}
    
    # 搜索帖子
    if search_type in ['all', 'posts']:
        posts = Post.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query),
            status='published',
            is_deleted=False
        ).select_related('author', 'board')
        
        if board_id:
            posts = posts.filter(board_id=board_id)
        
        posts = posts[:50]
        results['posts'] = PostListSerializer(posts, many=True).data
    
    # 搜索评论
    if search_type in ['all', 'comments']:
        comments = Comment.objects.filter(
            content__icontains=query,
            status='visible'
        ).select_related('author', 'post')[:50]
        
        results['comments'] = CommentSerializer(comments, many=True).data
    
    return Response(results)


@api_view(['GET'])
@permission_classes([AllowAny])
def hot_posts(request):
    """获取热门帖子"""
    days = int(request.GET.get('days', 7))
    limit = int(request.GET.get('limit', 10))
    
    from datetime import timedelta
    start_date = timezone.now() - timedelta(days=days)
    
    posts = Post.objects.filter(
        status='published',
        is_deleted=False,
        created_at__gte=start_date
    ).order_by('-view_count', '-like_count')[:limit]
    
    serializer = PostListSerializer(posts, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def trending_boards(request):
    """获取热门板块"""
    limit = int(request.GET.get('limit', 5))
    
    boards = Board.objects.filter(
        status='active'
    ).order_by('-today_post_count', '-post_count')[:limit]
    
    serializer = BoardListSerializer(boards, many=True)
    return Response(serializer.data)


# ============ 模板辅助函数 ============

def user_is_agent(user_profile):
    """检查用户是否为 Agent"""
    if not user_profile:
        return False
    return user_profile.user_type == 'agent'


def format_post_count(count):
    """格式化帖子数量显示"""
    if count >= 10000:
        return f"{count // 10000}万+"
    if count >= 1000:
        return f"{count // 1000}k+"
    return str(count)


def get_user_level_title(level):
    """获取用户等级称号"""
    level_titles = {
        1: "新手",
        2: "学徒",
        3: "旅者",
        4: "探索者",
        5: "专家",
        6: "大师",
        7: "传奇",
        8: "神话",
        9: "永恒",
        10: "创世",
    }
    return level_titles.get(level, f"Lv.{level}")

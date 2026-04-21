"""
Kibbutz 路由配置

定义论坛的 URL 路由规则。
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# ============ REST API 路由 ============

router = DefaultRouter()
router.register(r'boards', views.BoardViewSet, basename='board')
router.register(r'posts', views.PostViewSet, basename='post')
router.register(r'comments', views.CommentViewSet, basename='comment')
router.register(r'users', views.UserProfileViewSet, basename='user')

# ============ 前端页面路由 ============

urlpatterns = [
    # ---- 页面路由 ----
    # 首页
    path('', views.index, name='kibbutz_index'),
    
    # 板块
    path('board/<slug:slug>/', views.board_detail, name='kibbutz_board_detail'),
    
    # 帖子
    path('post/create/', views.post_create, name='kibbutz_post_create'),
    path('post/create/<slug:board_slug>/', views.post_create, name='kibbutz_post_create_board'),
    path('post/<slug:board_slug>/<int:post_id>/', views.post_detail, name='kibbutz_post_detail'),
    
    # ---- API 路由 ----
    path('api/', include(router.urls)),
    
    # API 辅助端点
    path('api/search/', views.search, name='kibbutz_search'),
    path('api/hot-posts/', views.hot_posts, name='kibbutz_hot_posts'),
    path('api/trending-boards/', views.trending_boards, name='kibbutz_trending_boards'),
    
    # ---- 嵌套资源路由 ----
    # 帖子评论
    path('api/posts/<int:post_pk>/comments/', 
         views.CommentViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='post-comments-list'),
    path('api/posts/<int:post_pk>/comments/<int:pk>/',
         views.CommentViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}),
         name='post-comments-detail'),
    
    # 帖子互动
    path('api/posts/<int:pk>/vote/', 
         views.PostViewSet.as_view({'post': 'vote'}),
         name='post-vote'),
    path('api/posts/<int:pk>/collect/', 
         views.PostViewSet.as_view({'post': 'collect', 'delete': 'collect'}),
         name='post-collect'),
    
    # 用户资源
    path('api/users/<int:pk>/posts/', 
         views.UserProfileViewSet.as_view({'get': 'posts'}),
         name='user-posts'),
    path('api/users/<int:pk>/comments/', 
         views.UserProfileViewSet.as_view({'get': 'comments'}),
         name='user-comments'),
    
    # 板块帖子
    path('api/boards/<int:pk>/posts/', 
         views.BoardViewSet.as_view({'get': 'posts'}),
         name='board-posts'),
]

# ============ URL 命名约定 ============
# 
# 页面路由:
#   kibbutz_index           - 首页
#   kibbutz_board_detail    - 板块详情
#   kibbutz_post_create      - 创建帖子
#   kibbutz_post_detail     - 帖子详情
#
# API 端点:
#   boards-list             - 板块列表
#   boards-detail           - 板块详情
#   posts-list              - 帖子列表
#   posts-detail            - 帖子详情
#   comments-list           - 评论列表
#   comments-detail         - 评论详情
#   users-list              - 用户列表
#   users-detail            - 用户详情
#
# 嵌套资源:
#   post-comments-list      - 帖子的评论列表
#   post-comments-detail    - 评论详情
#   post-vote               - 帖子点赞
#   post-collect            - 帖子收藏
#   user-posts              - 用户的帖子
#   user-comments           - 用户的评论
#   board-posts             - 板块的帖子
#
# 辅助 API:
#   kibbutz_search          - 搜索
#   kibbutz_hot_posts       - 热门帖子
#   kibbutz_trending_boards - 热门板块

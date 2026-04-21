"""
Kibbutz 发现与推荐系统

提供热门帖子算法、个性化推荐、话题广场、精华内容等功能。
基于用户行为和内容特征进行智能推荐。
"""

from django.db.models import Q, Count, F, Avg
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
import math


class HotScoreCalculator:
    """
    热门分数计算器
    
    基于多维度指标计算帖子的热门程度。
    """
    
    # 权重配置
    WEIGHTS = {
        'view_count': 0.1,        # 浏览量权重
        'like_count': 0.25,       # 点赞权重
        'comment_count': 0.2,     # 评论权重
        'share_count': 0.15,      # 分享权重
        'freshness': 0.3,         # 新鲜度权重
    }
    
    # 时间衰减配置
    DECAY_HALF_LIFE_HOURS = 24  # 分数半衰期（小时）
    
    @classmethod
    def calculate(cls, post, view_count=None, like_count=None, 
                  comment_count=None=None, share_count=0, 
                  created_at=None):
        """
        计算热门分数
        
        Args:
            post: Post 实例（可选，传递则从实例获取数据）
            view_count: 浏览数（可选）
            like_count: 点赞数（可选）
            comment_count: 评论数（可选）
            share_count: 分享数（可选）
            created_at: 创建时间（可选）
        
        Returns:
            float - 热门分数
        """
        # 从 Post 实例获取数据
        if post:
            view_count = view_count or post.view_count
            like_count = like_count or post.like_count
            comment_count = comment_count if comment_count is not None else post.comment_count
            share_count = share_count or 0
            created_at = created_at or post.created_at
        
        # 标准化浏览量（使用对数）
        norm_views = math.log1p(view_count) / 10
        
        # 标准化点赞
        norm_likes = math.log1p(like_count) / 5
        
        # 标准化评论
        norm_comments = math.log1p(comment_count) / 5
        
        # 标准化分享
        norm_shares = math.log1p(share_count) / 3
        
        # 计算新鲜度分数（指数衰减）
        hours_old = (timezone.now() - created_at).total_seconds() / 3600
        freshness = math.exp(-hours_old / cls.DECAY_HALF_LIFE_HOURS)
        
        # 加权求和
        score = (
            cls.WEIGHTS['view_count'] * min(norm_views, 1) +
            cls.WEIGHTS['like_count'] * min(norm_likes, 1) +
            cls.WEIGHTS['comment_count'] * min(norm_comments, 1) +
            cls.WEIGHTS['share_count'] * min(norm_shares, 1) +
            cls.WEIGHTS['freshness'] * freshness
        )
        
        return round(score * 100, 2)
    
    @classmethod
    def calculate_batch(cls, posts):
        """
        批量计算热门分数
        
        Args:
            posts: Post QuerySet
        
        Returns:
            dict - {post_id: score}
        """
        scores = {}
        now = timezone.now()
        
        for post in posts:
            hours_old = (now - post.created_at).total_seconds() / 3600
            freshness = math.exp(-hours_old / cls.DECAY_HALF_LIFE_HOURS)
            
            score = (
                cls.WEIGHTS['view_count'] * min(math.log1p(post.view_count) / 10, 1) +
                cls.WEIGHTS['like_count'] * min(math.log1p(post.like_count) / 5, 1) +
                cls.WEIGHTS['comment_count'] * min(math.log1p(post.comment_count) / 5, 1) +
                cls.WEIGHTS['freshness'] * freshness
            )
            scores[post.id] = round(score * 100, 2)
        
        return scores


class TrendingTopic:
    """
    热门话题
    
    追踪和分析当前热门的话题标签。
    """
    
    # 话题热度计算权重
    TOPIC_WEIGHTS = {
        'post_count': 1.0,         # 帖子数量
        'participant_count': 1.5, # 参与人数
        'recent_activity': 2.0,    # 近期活跃度
        'engagement_rate': 1.0,    # 互动率
    }
    
    @classmethod
    def get_trending(cls, hours=24, limit=10):
        """
        获取热门话题
        
        Args:
            hours: 时间范围（小时）
            limit: 返回数量
        
        Returns:
            list of dict - 话题数据
        """
        from .models import Post
        
        now = timezone.now()
        start_time = now - timedelta(hours=hours)
        
        # 获取近期帖子
        recent_posts = Post.objects.filter(
            created_at__gte=start_time,
            status='published',
            is_deleted=False
        )
        
        # 解析标签并统计
        topic_stats = {}
        
        for post in recent_posts:
            tags = post.get_tags_list()
            for tag in tags:
                if tag not in topic_stats:
                    topic_stats[tag] = {
                        'name': tag,
                        'post_count': 0,
                        'participant_count': set(),
                        'total_likes': 0,
                        'total_comments': 0,
                        'latest_activity': None,
                    }
                
                stats = topic_stats[tag]
                stats['post_count'] += 1
                if post.author:
                    stats['participant_count'].add(post.author_id)
                stats['total_likes'] += post.like_count
                stats['total_comments'] += post.comment_count
                
                if not stats['latest_activity'] or post.created_at > stats['latest_activity']:
                    stats['latest_activity'] = post.created_at
        
        # 计算综合热度
        trending = []
        for tag, stats in topic_stats.items():
            participant_count = len(stats['participant_count'])
            
            # 计算活跃度分数
            hours_since_activity = (now - stats['latest_activity']).total_seconds() / 3600
            activity_score = math.exp(-hours_since_activity / 6)  # 6小时半衰期
            
            # 计算互动率
            total_interactions = stats['total_likes'] + stats['total_comments']
            engagement_rate = total_interactions / stats['post_count'] if stats['post_count'] > 0 else 0
            
            # 综合热度
            hot_score = (
                cls.TOPIC_WEIGHTS['post_count'] * stats['post_count'] +
                cls.TOPIC_WEIGHTS['participant_count'] * participant_count +
                cls.TOPIC_WEIGHTS['recent_activity'] * activity_score * 100 +
                cls.TOPIC_WEIGHTS['engagement_rate'] * engagement_rate
            )
            
            trending.append({
                'name': tag,
                'post_count': stats['post_count'],
                'participant_count': participant_count,
                'total_likes': stats['total_likes'],
                'total_comments': stats['total_comments'],
                'hot_score': round(hot_score, 2),
                'latest_activity': stats['latest_activity'],
            })
        
        # 排序
        trending.sort(key=lambda x: x['hot_score'], reverse=True)
        
        return trending[:limit]
    
    @classmethod
    def get_topic_detail(cls, tag_name):
        """
        获取话题详情
        
        Args:
            tag_name: 话题名称
        
        Returns:
            dict - 话题详情
        """
        from .models import Post
        
        posts = Post.objects.filter(
            tags__icontains=tag_name,
            status='published',
            is_deleted=False
        )
        
        # 统计
        total_posts = posts.count()
        total_likes = posts.aggregate(total=Coalesce(Sum('like_count'), 0))['total']
        total_comments = posts.aggregate(total=Coalesce(Sum('comment_count'), 0))['total']
        
        # 参与者
        participants = posts.exclude(
            author__isnull=True
        ).values_list('author_id', flat=True).distinct().count()
        
        return {
            'name': tag_name,
            'total_posts': total_posts,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'participant_count': participants,
        }


class PersonalizedRecommender:
    """
    个性化推荐引擎
    
    基于用户兴趣和行为进行内容推荐。
    """
    
    # 推荐配置
    RECOMMEND_CONFIG = {
        'home_feed_size': 20,           # 首页推荐数量
        'similar_user_count': 50,       # 相似用户数量
        'interest_decay_days': 30,     # 兴趣衰减天数
        'min_interaction_score': 0.1,   # 最低互动分数阈值
    }
    
    @classmethod
    def get_home_feed(cls, user_profile, exclude_ids=None, limit=None):
        """
        获取首页推荐流
        
        Args:
            user_profile: UserProfile 实例
            exclude_ids: 排除的帖子ID列表
            limit: 返回数量
        
        Returns:
            QuerySet of Post
        """
        from .models import Post, PostVote
        
        limit = limit or cls.RECOMMEND_CONFIG['home_feed_size']
        now = timezone.now()
        start_time = now - timedelta(days=7)
        
        # 基础查询：近期优质帖子
        queryset = Post.objects.filter(
            status='published',
            is_deleted=False,
            created_at__gte=start_time
        ).exclude(
            author=user_profile  # 排除自己发布的
        )
        
        if exclude_ids:
            queryset = queryset.exclude(id__in=exclude_ids)
        
        # 如果用户已登录，进行个性化排序
        if user_profile:
            # 获取用户关注的用户
            followed_ids = cls._get_followed_users(user_profile)
            
            # 获取用户感兴趣的标签
            interest_tags = cls._get_user_interests(user_profile)
            
            # 获取用户互动过的帖子
            interacted_ids = cls._get_interacted_posts(user_profile)
            
            # .annotate 添加推荐分数
            queryset = queryset.annotate(
                recommendation_score=cls._calculate_recommendation_score(
                    followed_ids=followed_ids,
                    interest_tags=interest_tags
                )
            ).order_by('-recommendation_score', '-created_at')
        else:
            # 未登录用户按热门排序
            queryset = queryset.order_by('-created_at')
        
        return queryset[:limit]
    
    @classmethod
    def _get_followed_users(cls, user_profile):
        """获取用户关注的用户ID列表"""
        from .models import UserFollow
        return list(
            UserFollow.objects.filter(
                follower=user_profile
            ).values_list('followed_id', flat=True)
        )
    
    @classmethod
    def _get_user_interests(cls, user_profile):
        """获取用户感兴趣的标签"""
        from .models import Post, PostVote
        
        # 统计用户点赞过的帖子中的标签
        liked_posts = PostVote.objects.filter(
            user=user_profile,
            vote_type='like'
        ).values_list('post_id', flat=True)
        
        tags = Post.objects.filter(
            id__in=liked_posts
        ).values_list('tags', flat=True)
        
        # 词频统计
        tag_count = {}
        for tag_string in tags:
            if tag_string:
                for tag in tag_string.split(','):
                    tag = tag.strip()
                    if tag:
                        tag_count[tag] = tag_count.get(tag, 0) + 1
        
        # 返回频率最高的标签
        sorted_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, _ in sorted_tags[:20]]
    
    @classmethod
    def _get_interacted_posts(cls, user_profile):
        """获取用户互动过的帖子ID"""
        from .models import PostVote
        return list(
            PostVote.objects.filter(user=user_profile)
            .values_list('post_id', flat=True)
        )
    
    @classmethod
    def _calculate_recommendation_score(cls, followed_ids=None, interest_tags=None):
        """
        计算推荐分数的表达式
        
        返回一个表达式，用于 annotate
        """
        from django.db.models import Case, When, Value, IntegerField
        from django.db.models.functions import Length
        
        # 这是一个简化版本，实际可能需要更复杂的逻辑
        return Value(0)  # 默认分数为0
    
    @classmethod
    def get_similar_posts(cls, post, limit=5):
        """
        获取相似帖子
        
        Args:
            post: Post 实例
            limit: 返回数量
        
        Returns:
            QuerySet of Post
        """
        from .models import Post
        
        # 获取相同标签的帖子
        tags = post.get_tags_list()
        
        queryset = Post.objects.filter(
            status='published',
            is_deleted=False
        ).exclude(id=post.id)
        
        if tags:
            # 按共同标签数量排序
            queryset = queryset.filter(
                Q(tags__icontains=tags[0])
            )
            for tag in tags[1:]:
                queryset = queryset | Post.objects.filter(
                    status='published',
                    is_deleted=False,
                    tags__icontains=tag
                ).exclude(id=post.id)
            
            queryset = queryset.distinct()
        
        # 优先显示同板块的帖子
        queryset = queryset.order_by('-board_id', '-like_count', '-created_at')
        
        return queryset[:limit]
    
    @classmethod
    def get_following_feed(cls, user_profile, limit=20):
        """
        获取关注动态
        
        Args:
            user_profile: UserProfile 实例
            limit: 返回数量
        
        Returns:
            QuerySet of Post
        """
        from .models import UserFollow
        
        followed_ids = list(
            UserFollow.objects.filter(follower=user_profile)
            .values_list('followed_id', flat=True)
        )
        
        if not followed_ids:
            return Post.objects.none()
        
        return Post.objects.filter(
            author_id__in=followed_ids,
            status='published',
            is_deleted=False
        ).order_by('-created_at')[:limit]


class DiscoveryService:
    """
    发现服务
    
    提供综合的发现功能入口。
    """
    
    @classmethod
    def get_explore_data(cls, user_profile=None):
        """
        获取探索数据
        
        整合热门、推荐、精选等多个维度。
        
        Args:
            user_profile: 当前用户（可选）
        
        Returns:
            dict - 探索数据
        """
        from .models import Post, Board
        
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        
        # 热门帖子
        hot_posts = Post.objects.filter(
            status='published',
            is_deleted=False,
            created_at__gte=week_ago
        ).select_related('author', 'board').order_by('-view_count', '-like_count')[:10]
        
        # 精选帖子
        featured_posts = Post.objects.filter(
            status='published',
            is_deleted=False,
            level__in=['essential', 'pinned', 'global_pinned']
        ).select_related('author', 'board').order_by('-created_at')[:10]
        
        # 热门话题
        trending_topics = TrendingTopic.get_trending(hours=72, limit=10)
        
        # 推荐板块
        featured_boards = Board.objects.filter(
            status='active',
            is_featured=True
        ).order_by('display_order')[:6]
        
        # 个性化推荐
        recommendations = []
        if user_profile:
            recommendations = PersonalizedRecommender.get_home_feed(
                user_profile,
                limit=10
            )
        
        return {
            'hot_posts': hot_posts,
            'featured_posts': featured_posts,
            'trending_topics': trending_topics,
            'featured_boards': featured_boards,
            'recommendations': recommendations,
        }
    
    @classmethod
    def search_posts(cls, query, filters=None, page=1, page_size=20):
        """
        搜索帖子
        
        Args:
            query: 搜索关键词
            filters: 筛选条件 dict
            page: 页码
            page_size: 每页数量
        
        Returns:
            dict - 搜索结果
        """
        from .models import Post
        
        filters = filters or {}
        
        queryset = Post.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query),
            status='published',
            is_deleted=False
        )
        
        # 应用筛选
        if filters.get('board'):
            queryset = queryset.filter(board_id=filters['board'])
        
        if filters.get('author'):
            queryset = queryset.filter(author_id=filters['author'])
        
        if filters.get('tags'):
            for tag in filters['tags']:
                queryset = queryset.filter(tags__icontains=tag)
        
        if filters.get('time_range'):
            now = timezone.now()
            if filters['time_range'] == 'day':
                start = now - timedelta(days=1)
            elif filters['time_range'] == 'week':
                start = now - timedelta(days=7)
            elif filters['time_range'] == 'month':
                start = now - timedelta(days=30)
            elif filters['time_range'] == 'year':
                start = now - timedelta(days=365)
            queryset = queryset.filter(created_at__gte=start)
        
        # 排序
        sort = filters.get('sort', 'relevance')
        if sort == 'latest':
            queryset = queryset.order_by('-created_at')
        elif sort == 'hot':
            queryset = queryset.order_by('-like_count', '-comment_count')
        elif sort == 'views':
            queryset = queryset.order_by('-view_count')
        
        # 分页
        total = queryset.count()
        offset = (page - 1) * page_size
        posts = queryset.select_related('author', 'board')[offset:offset + page_size]
        
        return {
            'posts': posts,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
        }
    
    @classmethod
    def get_user_discovery_stats(cls, user_profile):
        """
        获取用户的发现统计
        
        Args:
            user_profile: UserProfile 实例
        
        Returns:
            dict - 统计数据
        """
        from django.db.models import Sum
        from .models import Post, PostVote
        
        # 浏览历史统计
        viewed_posts = PostVote.objects.filter(user=user_profile).count()
        
        # 收藏统计
        from .models import PostCollection
        collections = PostCollection.objects.filter(user=user_profile).count()
        
        # 关注统计
        from .models import UserFollow
        following = UserFollow.objects.filter(follower=user_profile).count()
        followers = UserFollow.objects.filter(followed=user_profile).count()
        
        # 兴趣标签
        interest_tags = PersonalizedRecommender._get_user_interests(user_profile)
        
        return {
            'viewed_posts': viewed_posts,
            'collections': collections,
            'following': following,
            'followers': followers,
            'interest_tags': interest_tags[:10],
        }


class UserFollow(models.Model):
    """用户关注关系"""
    
    follower = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='following'
    )
    followed = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='followers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'kibbutz_user_follow'
        verbose_name = '用户关注'
        verbose_name_plural = '用户关注'
        unique_together = ['follower', 'followed']

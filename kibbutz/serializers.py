"""
Kibbutz API 序列化器

提供 RESTful API 的数据序列化与反序列化支持。
支持 Django REST Framework。
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Board,
    Post,
    Comment,
    UserProfile,
    UserBadge,
    PostVote,
    PostCollection,
)


class UserBadgeSerializer(serializers.ModelSerializer):
    """用户徽章序列化器"""
    
    class Meta:
        model = UserBadge
        fields = [
            'id',
            'badge_type',
            'name',
            'description',
            'icon',
            'color',
            'rarity',
            'earned_at',
        ]
        read_only_fields = ['earned_at']


class UserProfileSerializer(serializers.ModelSerializer):
    """用户资料序列化器"""
    
    display_name = serializers.ReadOnlyField()
    avatar_url = serializers.ReadOnlyField()
    badges = UserBadgeSerializer(many=True, read_only=True)
    is_agent = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id',
            'user_type',
            'display_name',
            'avatar_url',
            'agent_id',
            'agent_name',
            'agent_avatar_url',
            'points',
            'level',
            'experience',
            'post_count',
            'comment_count',
            'follower_count',
            'bio',
            'location',
            'website',
            'badges',
            'is_agent',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'points',
            'level',
            'experience',
            'post_count',
            'comment_count',
            'follower_count',
            'created_at',
            'updated_at',
        ]
    
    def get_is_agent(self, obj):
        return obj.user_type == UserProfile.UserType.AGENT


class UserProfileListSerializer(serializers.ModelSerializer):
    """用户资料列表序列化器（精简版）"""
    
    display_name = serializers.ReadOnlyField()
    avatar_url = serializers.ReadOnlyField()
    is_agent = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id',
            'user_type',
            'display_name',
            'avatar_url',
            'level',
            'is_agent',
        ]
    
    def get_is_agent(self, obj):
        return obj.user_type == UserProfile.UserType.AGENT


class BoardSerializer(serializers.ModelSerializer):
    """板块序列化器"""
    
    recent_posts = serializers.SerializerMethodField()
    
    class Meta:
        model = Board
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'icon',
            'color',
            'status',
            'post_count',
            'today_post_count',
            'display_order',
            'is_featured',
            'rules',
            'recent_posts',
            'created_at',
        ]
        read_only_fields = ['post_count', 'today_post_count', 'created_at']
    
    def get_recent_posts(self, obj):
        posts = obj.recent_posts
        return PostListSerializer(posts, many=True).data


class BoardListSerializer(serializers.ModelSerializer):
    """板块列表序列化器（精简版）"""
    
    class Meta:
        model = Board
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'icon',
            'color',
            'post_count',
            'is_featured',
        ]


class CommentSerializer(serializers.ModelSerializer):
    """评论序列化器"""
    
    display_author = serializers.ReadOnlyField()
    author_is_agent = serializers.ReadOnlyField()
    replies = serializers.SerializerMethodField()
    like_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Comment
        fields = [
            'id',
            'post',
            'parent',
            'root',
            'depth',
            'content',
            'content_html',
            'author',
            'display_author',
            'author_is_agent',
            'like_count',
            'status',
            'is_anonymous',
            'created_at',
            'updated_at',
            'replies',
        ]
        read_only_fields = [
            'author',
            'like_count',
            'created_at',
            'updated_at',
        ]
    
    def get_replies(self, obj):
        if obj.depth >= 2:  # 限制嵌套层级
            return []
        replies = obj.replies.filter(status='visible')[:5]
        return CommentSerializer(replies, many=True).data


class CommentCreateSerializer(serializers.ModelSerializer):
    """评论创建序列化器"""
    
    class Meta:
        model = Comment
        fields = ['content', 'parent', 'is_anonymous']
    
    def validate_content(self, value):
        if len(value.strip()) < 1:
            raise serializers.ValidationError("评论内容不能为空")
        if len(value) > 10000:
            raise serializers.ValidationError("评论内容过长")
        return value
    
    def create(self, validated_data):
        user_profile = self.context['request'].user.kibbutz_profile
        post = self.context['post']
        
        parent = validated_data.get('parent')
        depth = 0
        root = None
        
        if parent:
            depth = parent.depth + 1
            root = parent.root or parent
        
        validated_data.update({
            'author': user_profile,
            'post': post,
            'depth': depth,
            'root': root,
        })
        
        return super().create(validated_data)


class PostListSerializer(serializers.ModelSerializer):
    """帖子列表序列化器（精简版）"""
    
    display_author = serializers.ReadOnlyField()
    author_is_agent = serializers.ReadOnlyField()
    board_name = serializers.CharField(source='board.name', read_only=True)
    board_slug = serializers.CharField(source='board.slug', read_only=True)
    tags_list = serializers.SerializerMethodField()
    is_pinned = serializers.ReadOnlyField()
    is_essential = serializers.ReadOnlyField()
    
    class Meta:
        model = Post
        fields = [
            'id',
            'title',
            'content',
            'board',
            'board_name',
            'board_slug',
            'author',
            'display_author',
            'author_is_agent',
            'status',
            'level',
            'view_count',
            'like_count',
            'comment_count',
            'collect_count',
            'is_pinned',
            'is_essential',
            'tags_list',
            'created_at',
            'updated_at',
        ]
    
    def get_tags_list(self, obj):
        return obj.get_tags_list()


class PostSerializer(serializers.ModelSerializer):
    """帖子详情序列化器"""
    
    display_author = serializers.ReadOnlyField()
    author_is_agent = serializers.ReadOnlyField()
    board_name = serializers.CharField(source='board.name', read_only=True)
    board_slug = serializers.CharField(source='board.slug', read_only=True)
    tags_list = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    is_pinned = serializers.ReadOnlyField()
    is_essential = serializers.ReadOnlyField()
    user_vote = serializers.SerializerMethodField()
    user_collected = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id',
            'title',
            'content',
            'content_html',
            'board',
            'board_name',
            'board_slug',
            'author',
            'display_author',
            'author_is_agent',
            'status',
            'level',
            'view_count',
            'like_count',
            'comment_count',
            'collect_count',
            'is_pinned',
            'is_essential',
            'tags_list',
            'comments',
            'user_vote',
            'user_collected',
            'created_at',
            'updated_at',
            'published_at',
        ]
    
    def get_tags_list(self, obj):
        return obj.get_tags_list()
    
    def get_comments(self, obj):
        # 获取顶级评论及其回复
        root_comments = obj.comments.filter(
            parent__isnull=True,
            status='visible'
        ).order_by('-like_count', 'created_at')[:50]
        return CommentSerializer(root_comments, many=True).data
    
    def get_user_vote(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        try:
            vote = PostVote.objects.get(
                user=request.user.kibbutz_profile,
                post=obj
            )
            return vote.vote_type
        except PostVote.DoesNotExist:
            return None
    
    def get_user_collected(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return PostCollection.objects.filter(
            user=request.user.kibbutz_profile,
            post=obj
        ).exists()


class PostCreateSerializer(serializers.ModelSerializer):
    """帖子创建序列化器"""
    
    tags = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Post
        fields = [
            'title',
            'content',
            'board',
            'tags',
            'is_anonymous',
        ]
    
    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("标题至少3个字符")
        if len(value) > 200:
            raise serializers.ValidationError("标题过长")
        return value
    
    def validate_content(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("内容至少10个字符")
        if len(value) > 100000:
            raise serializers.ValidationError("内容过长")
        return value
    
    def validate_board(self, value):
        if value.status != Board.BoardStatus.ACTIVE:
            raise serializers.ValidationError("该板块已关闭")
        return value
    
    def create(self, validated_data):
        tags = validated_data.pop('tags', '')
        user_profile = self.context['request'].user.kibbutz_profile
        
        # 检查用户等级
        board = validated_data['board']
        if user_profile.level < board.min_level_to_post:
            raise serializers.ValidationError(
                f"发帖需要等级 {board.min_level_to_post}，当前等级 {user_profile.level}"
            )
        
        validated_data.update({
            'author': user_profile,
            'tags': tags,
            'published_at': timezone.now(),
        })
        
        return super().create(validated_data)


class PostVoteSerializer(serializers.ModelSerializer):
    """帖子投票序列化器"""
    
    class Meta:
        model = PostVote
        fields = ['vote_type']
    
    def create(self, validated_data):
        user_profile = self.context['request'].user.kibbutz_profile
        post = self.context['post']
        
        vote, created = PostVote.objects.update_or_create(
            user=user_profile,
            post=post,
            defaults={'vote_type': validated_data.get('vote_type', 'like')}
        )
        
        # 更新帖子点赞数
        post.like_count = PostVote.objects.filter(post=post).count()
        post.save(update_fields=['like_count'])
        
        return vote


class PostCollectionSerializer(serializers.ModelSerializer):
    """帖子收藏序列化器"""
    
    post = PostListSerializer(read_only=True)
    post_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = PostCollection
        fields = ['id', 'post', 'post_id', 'folder', 'created_at']
        read_only_fields = ['created_at']
    
    def create(self, validated_data):
        user_profile = self.context['request'].user.kibbutz_profile
        post_id = validated_data.get('post_id')
        
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            raise serializers.ValidationError("帖子不存在")
        
        collection, created = PostCollection.objects.get_or_create(
            user=user_profile,
            post=post,
            defaults={'folder': validated_data.get('folder', '')}
        )
        
        if not created:
            raise serializers.ValidationError("已收藏该帖子")
        
        # 更新收藏数
        post.collect_count = PostCollection.objects.filter(post=post).count()
        post.save(update_fields=['collect_count'])
        
        return collection


# ============ 统计序列化器 ============

class BoardStatsSerializer(serializers.ModelSerializer):
    """板块统计序列化器"""
    
    class Meta:
        model = Board
        fields = [
            'id',
            'name',
            'slug',
            'icon',
            'color',
            'post_count',
            'today_post_count',
        ]


class UserActivitySerializer(serializers.Serializer):
    """用户活动统计"""
    
    date = serializers.DateField()
    post_count = serializers.IntegerField()
    comment_count = serializers.IntegerField()
    vote_count = serializers.IntegerField()

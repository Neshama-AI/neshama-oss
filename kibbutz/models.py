"""
Kibbutz 数据模型

定义论坛核心实体：板块、帖子、评论、用户、徽章等
支持 Agent 与用户的区分标识。
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator


class UserProfile(models.Model):
    """
    用户扩展资料
    
    关联 Django 内置 User 模型，扩展用户属性。
    支持人类用户和 Agent 的区分。
    """
    
    class UserType(models.TextChoices):
        HUMAN = 'human', '人类用户'
        AGENT = 'agent', 'Agent'
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='kibbutz_profile'
    )
    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.HUMAN
    )
    
    # Agent 专属属性
    agent_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Agent 唯一标识"
    )
    agent_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Agent 显示名称"
    )
    agent_avatar_url = models.URLField(
        blank=True,
        help_text="Agent 头像 URL"
    )
    
    # 积分与等级
    points = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    level = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    experience = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # 用户统计
    post_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    follower_count = models.IntegerField(default=0)
    
    # 社交属性
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    
    # 设置
    is_anonymous = models.BooleanField(default=False)
    notification_enabled = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'kibbutz_user_profile'
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'
    
    def __str__(self):
        if self.user_type == self.UserType.AGENT:
            return f"Agent: {self.agent_name or self.user.username}"
        return self.user.username
    
    @property
    def display_name(self):
        """获取显示名称"""
        if self.user_type == self.UserType.AGENT:
            return self.agent_name or f"Agent_{self.user.username[:8]}"
        return self.user.username
    
    @property
    def avatar_url(self):
        """获取头像 URL"""
        if self.user_type == self.UserType.AGENT and self.agent_avatar_url:
            return self.agent_avatar_url
        # 可使用默认头像或 Gravatar
        return f"/static/kibbutz/images/default_avatar.png"


class UserBadge(models.Model):
    """
    用户徽章
    
    奖励用户在社区中的贡献和成就。
    """
    
    class BadgeType(models.TextChoices):
        SYSTEM = 'system', '系统徽章'
        ACHIEVEMENT = 'achievement', '成就徽章'
        SPECIAL = 'special', '特殊徽章'
    
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='badges'
    )
    badge_type = models.CharField(
        max_length=20,
        choices=BadgeType.choices,
        default=BadgeType.ACHIEVEMENT
    )
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200)
    icon = models.CharField(max_length=100, help_text="图标类名或 URL")
    color = models.CharField(max_length=20, default="#4A90D9")
    
    # 稀有度
    rarity = models.IntegerField(default=1, help_text="1-5 稀有度等级")
    
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'kibbutz_user_badge'
        verbose_name = '用户徽章'
        verbose_name_plural = '用户徽章'
        unique_together = ['user', 'name']
    
    def __str__(self):
        return f"{self.user.display_name} - {self.name}"


class Board(models.Model):
    """
    讨论板块
    
    按主题/领域划分的讨论区域。
    """
    
    class BoardStatus(models.TextChoices):
        ACTIVE = 'active', '正常'
        LOCKED = 'locked', '锁定'
        HIDDEN = 'hidden', '隐藏'
    
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.CharField(max_length=200)
    icon = models.CharField(max_length=100, default="bi-chat-square-text")
    color = models.CharField(max_length=20, default="#4A90D9")
    
    # 权限设置
    status = models.CharField(
        max_length=10,
        choices=BoardStatus.choices,
        default=BoardStatus.ACTIVE
    )
    min_level_to_post = models.IntegerField(default=1)
    min_level_to_view = models.IntegerField(default=1)
    requires_invitation = models.BooleanField(default=False)
    
    # 统计
    post_count = models.IntegerField(default=0)
    today_post_count = models.IntegerField(default=0)
    
    # 排序与显示
    display_order = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    
    # 板块规则
    rules = models.TextField(blank=True, help_text="板块规则说明")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'kibbutz_board'
        verbose_name = '讨论板块'
        verbose_name_plural = '讨论板块'
        ordering = ['display_order', '-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def recent_posts(self):
        """获取最近帖子"""
        return self.posts.filter(
            is_deleted=False,
            status='published'
        ).order_by('-created_at')[:10]


class Post(models.Model):
    """
    帖子
    
    论坛主题帖，包含标题和正文内容。
    """
    
    class PostStatus(models.TextChoices):
        DRAFT = 'draft', '草稿'
        PUBLISHED = 'published', '已发布'
        LOCKED = 'locked', '已锁定'
        DELETED = 'deleted', '已删除'
    
    class PostLevel(models.TextChoices):
        NORMAL = 'normal', '普通'
        PINNED = 'pinned', '置顶'
        GLOBAL_PINNED = 'global_pinned', '全局置顶'
        ESSENTIAL = 'essential', '精华'
    
    author = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='posts'
    )
    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    
    # 内容
    title = models.CharField(max_length=200)
    content = models.TextField()
    content_html = models.TextField(blank=True, help_text="渲染后的 HTML")
    
    # 状态与级别
    status = models.CharField(
        max_length=10,
        choices=PostStatus.choices,
        default=PostStatus.PUBLISHED
    )
    level = models.CharField(
        max_length=20,
        choices=PostLevel.choices,
        default=PostLevel.NORMAL
    )
    
    # 统计
    view_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    collect_count = models.IntegerField(default=0)
    
    # 用户交互记录（软删除标识）
    is_deleted = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)
    
    # 标签
    tags = models.CharField(
        max_length=200,
        blank=True,
        help_text="逗号分隔的标签"
    )
    
    # SEO
    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.CharField(max_length=300, blank=True)
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'kibbutz_post'
        verbose_name = '帖子'
        verbose_name_plural = '帖子'
        ordering = ['-level', '-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['board', '-created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['-view_count']),
            models.Index(fields=['-like_count']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def is_pinned(self):
        """是否置顶"""
        return self.level in [self.PostLevel.PINNED, self.PostLevel.GLOBAL_PINNED]
    
    @property
    def is_essential(self):
        """是否精华"""
        return self.level == self.PostLevel.ESSENTIAL
    
    @property
    def display_author(self):
        """显示的作者名"""
        if self.is_anonymous:
            return "匿名用户"
        return self.author.display_name if self.author else "[已删除]"
    
    @property
    def author_is_agent(self):
        """作者是否为 Agent"""
        return self.author.user_type == UserProfile.UserType.AGENT if self.author else False
    
    def get_tags_list(self):
        """获取标签列表"""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]
    
    def increment_view(self):
        """增加浏览量"""
        self.view_count = models.F('view_count') + 1
        Post.objects.filter(pk=self.pk).update(view_count=self.view_count + 1)
        self.view_count += 1


class Comment(models.Model):
    """
    评论
    
    对帖子的回复，支持嵌套评论。
    """
    
    class CommentStatus(models.TextChoices):
        VISIBLE = 'visible', '可见'
        DELETED = 'deleted', '已删除'
        HIDDEN = 'hidden', '已隐藏'
        REPORTED = 'reported', '已举报'
    
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='comments'
    )
    
    # 内容
    content = models.TextField()
    content_html = models.TextField(blank=True)
    
    # 层级关系（支持嵌套）
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    root = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='all_replies'
    )
    depth = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # 状态
    status = models.CharField(
        max_length=10,
        choices=CommentStatus.choices,
        default=CommentStatus.VISIBLE
    )
    
    # 统计
    like_count = models.IntegerField(default=0)
    
    # 用户设置
    is_anonymous = models.BooleanField(default=False)
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'kibbutz_comment'
        verbose_name = '评论'
        verbose_name_plural = '评论'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['author', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.display_author} - {self.content[:50]}"
    
    @property
    def display_author(self):
        """显示的作者名"""
        if self.is_anonymous:
            return "匿名用户"
        return self.author.display_name if self.author else "[已删除]"
    
    @property
    def author_is_agent(self):
        """作者是否为 Agent"""
        return self.author.user_type == UserProfile.UserType.AGENT if self.author else False


class PostVote(models.Model):
    """
    帖子点赞
    
    记录用户对帖子的点赞/踩行为。
    """
    
    class VoteType(models.TextChoices):
        LIKE = 'like', '点赞'
        DISLIKE = 'dislike', '点踩'
    
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    vote_type = models.CharField(
        max_length=10,
        choices=VoteType.choices,
        default=VoteType.LIKE
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'kibbutz_post_vote'
        verbose_name = '帖子点赞'
        verbose_name_plural = '帖子点赞'
        unique_together = ['user', 'post']
    
    def __str__(self):
        return f"{self.user.display_name} - {self.vote_type} - {self.post.title[:30]}"


class PostCollection(models.Model):
    """
    帖子收藏
    
    用户收藏的帖子列表。
    """
    
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='collections'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='collectors'
    )
    folder = models.CharField(max_length=50, blank=True, help_text="收藏夹名称")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'kibbutz_post_collection'
        verbose_name = '帖子收藏'
        verbose_name_plural = '帖子收藏'
        unique_together = ['user', 'post']
    
    def __str__(self):
        return f"{self.user.display_name} 收藏了 {self.post.title[:30]}"


# ============ 信号处理 ============

def update_post_count(sender, instance, action, **kwargs):
    """更新帖子数量统计"""
    if action in ['post_add', 'post_remove']:
        board = instance.board
        board.post_count = Post.objects.filter(
            board=board,
            is_deleted=False
        ).count()
        board.save()


def update_comment_count(sender, instance, action, **kwargs):
    """更新评论数量统计"""
    if action == 'post_save':
        post = instance.post
        post.comment_count = Comment.objects.filter(
            post=post,
            status='visible'
        ).count()
        post.save(update_fields=['comment_count'])

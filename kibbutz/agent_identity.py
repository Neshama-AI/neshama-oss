"""
Kibbutz Agent 身份认证与成长体系

定义 Agent 身份验证、发帖规则、成长联动等核心功能。
Agent 与用户在社群中有明确的区分和差异化的互动规则。
"""

import hashlib
import secrets
import re
from datetime import timedelta
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.validators import URLValidator
from django.conf import settings


class AgentVerification(models.Model):
    """
    Agent 身份验证记录
    
    确保 Agent 的身份真实，防止冒充。
    """
    
    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', '待验证'
        APPROVED = 'approved', '已通过'
        REJECTED = 'rejected', '已拒绝'
        EXPIRED = 'expired', '已过期'
        REVOKED = 'revoked', '已撤销'
    
    agent_profile = models.OneToOneField(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='verification_record'
    )
    
    # 验证信息
    verification_token = models.CharField(max_length=64, unique=True)
    verification_code = models.CharField(max_length=6, blank=True)
    
    # 来源信息
    agent_provider = models.CharField(
        max_length=50,
        help_text="Agent 提供方/平台"
    )
    agent_model = models.CharField(
        max_length=100,
        blank=True,
        help_text="Agent 使用的模型"
    )
    official_website = models.URLField(blank=True)
    official_account = models.CharField(
        max_length=100,
        blank=True,
        help_text="官方账号/频道"
    )
    
    # 验证状态
    status = models.CharField(
        max_length=15,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    
    # 审核信息
    reviewed_by = models.ForeignKey(
        'UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_verifications'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'kibbutz_agent_verification'
        verbose_name = 'Agent身份验证'
        verbose_name_plural = 'Agent身份验证'
    
    def __str__(self):
        return f"{self.agent_profile.display_name} - {self.status}"
    
    @classmethod
    def generate_token(cls):
        """生成验证令牌"""
        return secrets.token_hex(32)
    
    @classmethod
    def create_verification(cls, agent_profile, provider, model='', 
                           website='', account=''):
        """
        创建验证申请
        
        Args:
            agent_profile: Agent 的 UserProfile
            provider: 提供方名称
            model: 模型名称
            website: 官网
            account: 官方账号
        
        Returns:
            AgentVerification 实例
        """
        verification = cls.objects.create(
            agent_profile=agent_profile,
            verification_token=cls.generate_token(),
            agent_provider=provider,
            agent_model=model,
            official_website=website,
            official_account=account,
            status=cls.VerificationStatus.PENDING
        )
        return verification
    
    def approve(self, reviewer, notes=''):
        """通过验证"""
        self.status = self.VerificationStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.expires_at = timezone.now() + timedelta(days=365)
        self.save()
        
        # 触发验证奖励
        from .economy import EconomyService
        EconomyService.add_points(
            user_profile=self.agent_profile,
            amount=100,
            transaction_type='verification_reward',
            description='完成身份验证奖励'
        )
        
        return self
    
    def reject(self, reviewer, notes):
        """拒绝验证"""
        self.status = self.VerificationStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
        return self
    
    @property
    def is_verified(self):
        """是否已验证"""
        return self.status == self.VerificationStatus.APPROVED
    
    @property
    def is_expired(self):
        """是否过期"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at


class AgentPostRule(models.Model):
    """
    Agent 发帖规则配置
    
    定义 Agent 在社区发帖的行为规范。
    """
    
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=200)
    
    # 频率限制
    daily_post_limit = models.IntegerField(
        default=10,
        help_text="每日发帖上限"
    )
    hourly_post_limit = models.IntegerField(
        default=3,
        help_text="每小时发帖上限"
    )
    comment_limit_per_post = models.IntegerField(
        default=50,
        help_text="每个帖子最多评论数"
    )
    
    # 内容限制
    min_content_length = models.IntegerField(
        default=50,
        help_text="最小内容长度"
    )
    max_content_length = models.IntegerField(
        default=5000,
        help_text="最大内容长度"
    )
    requires_topic = models.BooleanField(
        default=True,
        help_text="是否必须选择话题"
    )
    
    # 互动限制
    max_mentions_per_post = models.IntegerField(
        default=5,
        help_text="每帖最多 @ 提及人数"
    )
    allow_self_reply = models.BooleanField(
        default=True,
        help_text="是否允许自问自答"
    )
    
    # 特殊权限
    can_create_board = models.BooleanField(default=False)
    can_pin_own_post = models.BooleanField(default=False)
    can_feature_post = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'kibbutz_agent_post_rule'
        verbose_name = 'Agent发帖规则'
        verbose_name_plural = 'Agent发帖规则'
    
    def __str__(self):
        return self.name


class AgentActivityLog(models.Model):
    """
    Agent 活动日志
    
    记录 Agent 的活动，用于监控和行为分析。
    """
    
    class ActivityType(models.TextChoices):
        POST = 'post', '发帖'
        COMMENT = 'comment', '评论'
        REPLY = 'reply', '回复'
        EDIT = 'edit', '编辑'
        DELETE = 'delete', '删除'
        MENTION = 'mention', '提及'
        FOLLOW = 'follow', '关注'
        LIKE = 'like', '点赞'
    
    agent = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='activity_logs'
    )
    
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices
    )
    
    # 关联内容
    related_post = models.ForeignKey(
        'Post',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_activity_logs'
    )
    related_comment = models.ForeignKey(
        'Comment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_activity_logs'
    )
    mentioned_users = models.JSONField(
        default=list,
        blank=True,
        help_text="提及的用户ID列表"
    )
    
    # 内容摘要
    content_preview = models.CharField(
        max_length=200,
        blank=True,
        help_text="内容预览"
    )
    
    # 元数据
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'kibbutz_agent_activity_log'
        verbose_name = 'Agent活动日志'
        verbose_name_plural = 'Agent活动日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent', '-created_at']),
            models.Index(fields=['activity_type']),
        ]
    
    def __str__(self):
        return f"{self.agent.display_name} - {self.activity_type}"


class AgentGrowth(models.Model):
    """
    Agent 成长体系
    
    记录 Agent 的成长数据，与 Soul 层联动。
    """
    
    class GrowthStage(models.TextChoices):
        NEWBIE = 'newbie', '新人'
        ACTIVE = 'active', '活跃'
        CONTRIBUTOR = 'contributor', '贡献者'
        EXPERT = 'expert', '专家'
        MASTER = 'master', '大师'
    
    agent_profile = models.OneToOneField(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='growth_record'
    )
    
    # 成长值
    growth_points = models.IntegerField(default=0)
    stage = models.CharField(
        max_length=20,
        choices=GrowthStage.choices,
        default=GrowthStage.NEWBIE
    )
    
    # 成长统计
    total_posts = models.IntegerField(default=0)
    total_comments = models.IntegerField(default=0)
    total_helpful_answers = models.IntegerField(default=0)
    total_received_likes = models.IntegerField(default=0)
    
    # 质量指标
    avg_response_time = models.IntegerField(
        default=0,
        help_text="平均回复时间（分钟）"
    )
    content_quality_score = models.FloatField(
        default=0.0,
        validators=[MaxValueValidator(100.0)]
    )
    
    # Soul 层联动
    soul_level = models.IntegerField(default=1)
    soul_experience = models.IntegerField(default=0)
    
    # 特殊能力
    special_abilities = models.JSONField(
        default=dict,
        blank=True,
        help_text="解锁的特殊能力"
    )
    
    # 徽章
    earned_badges = models.JSONField(
        default=list,
        blank=True,
        help_text="获得的成长徽章"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'kibbutz_agent_growth'
        verbose_name = 'Agent成长'
        verbose_name_plural = 'Agent成长'
    
    def __str__(self):
        return f"{self.agent_profile.display_name} - {self.stage}"
    
    @classmethod
    def get_stage_requirements(cls, stage):
        """获取阶段要求"""
        requirements = {
            cls.GrowthStage.NEWBIE: {'points': 0, 'posts': 0},
            cls.GrowthStage.ACTIVE: {'points': 100, 'posts': 10},
            cls.GrowthStage.CONTRIBUTOR: {'points': 500, 'posts': 50},
            cls.GrowthStage.EXPERT: {'points': 2000, 'posts': 200},
            cls.GrowthStage.MASTER: {'points': 10000, 'posts': 1000},
        }
        return requirements.get(stage, {})
    
    def check_stage_upgrade(self):
        """检查是否可以升级"""
        current_requirements = self.get_stage_requirements(self.stage)
        next_stage = None
        
        stages = list(self.GrowthStage.values)
        current_index = stages.index(self.stage)
        
        if current_index < len(stages) - 1:
            next_stage = stages[current_index + 1]
            next_requirements = self.get_stage_requirements(next_stage)
            
            if (self.growth_points >= next_requirements.get('points', float('inf')) and
                self.total_posts >= next_requirements.get('posts', 0)):
                return True, next_stage
        
        return False, None
    
    def add_growth_points(self, points, activity_type):
        """添加成长值"""
        self.growth_points += points
        
        # 更新统计
        if activity_type == 'post':
            self.total_posts += 1
        elif activity_type == 'comment':
            self.total_comments += 1
        elif activity_type == 'helpful':
            self.total_helpful_answers += 1
        elif activity_type == 'like':
            self.total_received_likes += 1
        
        # 检查升级
        can_upgrade, next_stage = self.check_stage_upgrade()
        if can_upgrade:
            self.stage = next_stage
        
        self.save()
        return can_upgrade, next_stage


class AgentIdentityService:
    """
    Agent 身份服务
    
    提供 Agent 身份验证和规则检查的核心逻辑。
    """
    
    # Agent 标识样式
    AGENT_BADGE_COLOR = '#8B5CF6'  # 紫色
    AGENT_BORDER_COLOR = '#A78BFA'
    AGENT_ICON = 'bi-robot'
    
    @classmethod
    def can_post(cls, agent_profile):
        """
        检查 Agent 是否可以发帖
        
        Args:
            agent_profile: Agent 的 UserProfile
        
        Returns:
            (bool, str, dict) - (是否可以, 原因, 限制信息)
        """
        # 检查是否验证
        try:
            verification = agent_profile.verification_record
            if not verification.is_verified:
                return False, "Agent 尚未完成身份验证", {}
            if verification.is_expired:
                return False, "Agent 身份验证已过期", {}
        except AgentVerification.DoesNotExist:
            return False, "Agent 未申请身份验证", {}
        
        # 检查发帖频率
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        hour_start = now - timedelta(hours=1)
        
        # 获取适用的规则
        rule = AgentPostRule.objects.filter(is_active=True).first()
        if not rule:
            return True, "无限制", {}
        
        # 检查每日发帖数
        today_posts = Post.objects.filter(
            author=agent_profile,
            created_at__gte=today_start
        ).count()
        
        if today_posts >= rule.daily_post_limit:
            return False, f"已达每日发帖上限 ({rule.daily_post_limit})", {
                'daily_limit': rule.daily_post_limit,
                'used': today_posts
            }
        
        # 检查每小时发帖数
        hour_posts = Post.objects.filter(
            author=agent_profile,
            created_at__gte=hour_start
        ).count()
        
        if hour_posts >= rule.hourly_post_limit:
            return False, f"发帖过于频繁，请等待", {
                'hourly_limit': rule.hourly_post_limit,
                'used': hour_posts
            }
        
        return True, "可以发帖", {
            'daily_remaining': rule.daily_post_limit - today_posts,
            'hourly_remaining': rule.hourly_post_limit - hour_posts
        }
    
    @classmethod
    def can_comment(cls, agent_profile, post):
        """
        检查 Agent 是否可以评论
        
        Args:
            agent_profile: Agent 的 UserProfile
            post: Post 实例
        
        Returns:
            (bool, str) - (是否可以, 原因)
        """
        rule = AgentPostRule.objects.filter(is_active=True).first()
        if not rule:
            return True, "无限制"
        
        # 检查该帖子的评论数
        comment_count = Comment.objects.filter(
            author=agent_profile,
            post=post
        ).count()
        
        if comment_count >= rule.comment_limit_per_post:
            return False, f"该帖子评论数已达上限 ({rule.comment_limit_per_post})"
        
        return True, "可以评论"
    
    @classmethod
    def validate_content(cls, content, content_type='post'):
        """
        验证 Agent 发布的内容
        
        Args:
            content: 内容文本
            content_type: 内容类型 ('post', 'comment')
        
        Returns:
            (bool, list) - (是否有效, 错误列表)
        """
        errors = []
        rule = AgentPostRule.objects.filter(is_active=True).first()
        
        if not rule:
            return True, []
        
        content_length = len(content.strip())
        
        if content_length < rule.min_content_length:
            errors.append(f"内容过短，至少需要 {rule.min_content_length} 字符")
        
        if content_length > rule.max_content_length:
            errors.append(f"内容过长，最多 {rule.max_content_length} 字符")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_mentions(cls, content):
        """
        验证内容中的 @ 提及
        
        Returns:
            (bool, list, list) - (是否有效, 提及的用户, 错误)
        """
        # 提取 @ 提及
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, content)
        
        rule = AgentPostRule.objects.filter(is_active=True).first()
        max_mentions = rule.max_mentions_per_post if rule else 5
        
        if len(mentions) > max_mentions:
            return False, mentions, [f"提及用户过多，最多 {max_mentions} 个"]
        
        # 验证用户存在
        from .models import UserProfile
        valid_users = []
        for username in mentions:
            try:
                user = UserProfile.objects.get(user__username=username)
                valid_users.append(user)
            except UserProfile.DoesNotExist:
                pass
        
        return True, valid_users, []
    
    @classmethod
    def get_agent_identity_data(cls, agent_profile):
        """
        获取 Agent 身份数据
        
        Args:
            agent_profile: Agent 的 UserProfile
        
        Returns:
            dict - 身份数据
        """
        data = {
            'display_name': agent_profile.display_name,
            'avatar_url': agent_profile.avatar_url,
            'is_verified': False,
            'verification_status': None,
            'provider': None,
            'growth_stage': None,
            'growth_points': 0,
            'badge_color': cls.AGENT_BADGE_COLOR,
            'border_color': cls.AGENT_BORDER_COLOR,
            'icon': cls.AGENT_ICON,
        }
        
        # 获取验证信息
        try:
            verification = agent_profile.verification_record
            data['is_verified'] = verification.is_verified
            data['verification_status'] = verification.status
            data['provider'] = verification.agent_provider
        except AgentVerification.DoesNotExist:
            pass
        
        # 获取成长信息
        try:
            growth = agent_profile.growth_record
            data['growth_stage'] = growth.stage
            data['growth_points'] = growth.growth_points
            data['total_posts'] = growth.total_posts
            data['total_comments'] = growth.total_comments
        except AgentGrowth.DoesNotExist:
            pass
        
        return data
    
    @classmethod
    def sync_with_soul_layer(cls, agent_profile, soul_data):
        """
        与 Soul 层同步数据
        
        Args:
            agent_profile: Agent 的 UserProfile
            soul_data: Soul 层数据 dict
        
        Returns:
            AgentGrowth 实例
        """
        growth, created = AgentGrowth.objects.get_or_create(
            agent_profile=agent_profile,
            defaults={
                'soul_level': soul_data.get('level', 1),
                'soul_experience': soul_data.get('experience', 0),
                'special_abilities': soul_data.get('abilities', {}),
            }
        )
        
        if not created:
            growth.soul_level = soul_data.get('level', growth.soul_level)
            growth.soul_experience = soul_data.get('experience', growth.soul_experience)
            growth.special_abilities = soul_data.get('abilities', growth.special_abilities)
            growth.save()
        
        return growth


# 导入 Post 和 Comment 模型（避免循环引用）
from .models import Post, Comment


class MaxValueValidator:
    """占位符，将在导入后使用"""
    pass

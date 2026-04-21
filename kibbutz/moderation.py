"""
Kibbutz 内容审核系统

提供版主/管理员体系、内容审核、举报机制、敏感词过滤等功能。
确保社区内容质量和健康环境。
"""

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
import re


class Moderator(models.Model):
    """
    版主/管理员
    
    定义用户在社区中的管理权限。
    """
    
    class Role(models.TextChoices):
        MODERATOR = 'moderator', '版主'
        ADMIN = 'admin', '管理员'
        SUPER_ADMIN = 'super_admin', '超级管理员'
    
    user = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='moderator_roles'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices
    )
    
    # 管辖范围
    board = models.ForeignKey(
        'Board',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='moderators',
        help_text="管辖板块，为空则管理全部"
    )
    
    # 权限
    can_pin = models.BooleanField(default=True)
    can_essential = models.BooleanField(default=True)
    can_lock = models.BooleanField(default=True)
    can_delete = models.BooleanField(default=True)
    can_ban = models.BooleanField(default=False)
    can_verify_agent = models.BooleanField(default=False)
    can_manage_rules = models.BooleanField(default=False)
    
    # 状态
    is_active = models.BooleanField(default=True)
    
    # 任命信息
    appointed_by = models.ForeignKey(
        'UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointed_moderators'
    )
    appointed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'kibbutz_moderator'
        verbose_name = '版主/管理员'
        verbose_name_plural = '版主/管理员'
    
    def __str__(self):
        scope = f"({self.board.name})" if self.board else "(全局)"
        return f"{self.user.display_name} - {self.get_role_display()} {scope}"
    
    @property
    def is_admin(self):
        """是否为管理员"""
        return self.role in [self.Role.ADMIN, self.Role.SUPER_ADMIN]
    
    @property
    def is_super_admin(self):
        """是否为超级管理员"""
        return self.role == self.Role.SUPER_ADMIN


class ModerationLog(models.Model):
    """
    审核日志
    
    记录所有管理操作。
    """
    
    class Action(models.TextChoices):
        PIN = 'pin', '置顶'
        UNPIN = 'unpin', '取消置顶'
        ESSENTIAL = 'essential', '设为精华'
        UNESSENTIAL = 'unessential', '取消精华'
        LOCK = 'lock', '锁定'
        UNLOCK = 'unlock', '解锁'
        DELETE = 'delete', '删除'
        RESTORE = 'restore', '恢复'
        WARN = 'warn', '警告'
        BAN = 'ban', '封禁'
        UNBAN = 'unban', '解封'
        MOVE = 'move', '移动'
    
    moderator = models.ForeignKey(
        'UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='moderation_logs'
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    
    # 涉及内容
    target_type = models.CharField(
        max_length=20,
        choices=[
            ('post', '帖子'),
            ('comment', '评论'),
            ('user', '用户'),
        ]
    )
    target_id = models.IntegerField()
    
    # 目标详情（冗余存储，便于查询）
    target_author = models.ForeignKey(
        'UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='moderation_received'
    )
    
    # 附加信息
    reason = models.TextField(blank=True)
    previous_state = models.JSONField(default=dict, blank=True)
    new_state = models.JSONField(default=dict, blank=True)
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'kibbutz_moderation_log'
        verbose_name = '审核日志'
        verbose_name_plural = '审核日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['moderator', '-created_at']),
            models.Index(fields=['target_type', 'target_id']),
        ]
    
    def __str__(self):
        return f"{self.moderator} {self.get_action_display()} {self.target_type} #{self.target_id}"


class Report(models.Model):
    """
    举报记录
    
    用户可以举报违规内容。
    """
    
    class ReportType(models.TextChoices):
        SPAM = 'spam', '垃圾广告'
        HARASSMENT = 'harassment', '人身攻击'
        INAPPROPRIATE = 'inappropriate', '不当内容'
        MISINFORMATION = 'misinformation', '虚假信息'
        COPYRIGHT = 'copyright', '侵权'
        OTHER = 'other', '其他'
    
    class ReportStatus(models.TextChoices):
        PENDING = 'pending', '待处理'
        REVIEWING = 'reviewing', '审核中'
        RESOLVED = 'resolved', '已处理'
        DISMISSED = 'dismissed', '已驳回'
    
    reporter = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='reports_made'
    )
    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices
    )
    
    # 被举报内容
    content_type = models.CharField(
        max_length=20,
        choices=[
            ('post', '帖子'),
            ('comment', '评论'),
        ]
    )
    content_id = models.IntegerField()
    content_author = models.ForeignKey(
        'UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_received'
    )
    
    # 内容预览
    content_preview = models.TextField()
    
    # 举报详情
    description = models.TextField()
    evidence_urls = models.JSONField(default=list, blank=True)
    
    # 状态
    status = models.CharField(
        max_length=15,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING
    )
    
    # 处理信息
    handler = models.ForeignKey(
        'UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_handled'
    )
    handled_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField(blank=True)
    
    # 重复举报检测
    duplicate_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='duplicates'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'kibbutz_report'
        verbose_name = '举报'
        verbose_name_plural = '举报'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['content_type', 'content_id']),
        ]
    
    def __str__(self):
        return f"#{self.id} {self.get_report_type_display()} - {self.get_status_display()}"


class SensitiveWord(models.Model):
    """
    敏感词库
    
    定义需要过滤的敏感词。
    """
    
    class WordType(models.TextChoices):
        SENSITIVE = 'sensitive', '敏感词'
        SLANG = 'slang', '俚语'
        AD = 'ad', '广告词'
        CUSTOM = 'custom', '自定义'
    
    class Action(models.TextChoices):
        WARN = 'warn', '警告'
        CENSOR = 'censor', '审核'
        REJECT = 'reject', '拒绝'
    
    word = models.CharField(max_length=100, unique=True)
    word_type = models.CharField(
        max_length=15,
        choices=WordType.choices,
        default=WordType.SENSITIVE
    )
    action = models.CharField(
        max_length=10,
        choices=Action.choices,
        default=Action.CENSOR
    )
    
    # 等级（1-5，越高越严格）
    level = models.IntegerField(default=1)
    
    # 替换规则
    replacement = models.CharField(
        max_length=100,
        blank=True,
        help_text="替换字符，如 ***"
    )
    
    # 自动处理
    auto_process = models.BooleanField(
        default=True,
        help_text="是否自动处理"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'kibbutz_sensitive_word'
        verbose_name = '敏感词'
        verbose_name_plural = '敏感词'
    
    def __str__(self):
        return f"{self.word} ({self.get_word_type_display()})"


class UserWarning(models.Model):
    """
    用户警告记录
    
    记录对用户的警告信息。
    """
    
    class WarningType(models.TextChoices):
        CONTENT = 'content', '内容违规'
        BEHAVIOR = 'behavior', '行为不当'
        SPAM = 'spam', '刷屏/垃圾'
        OTHER = 'other', '其他'
    
    user = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='warnings'
    )
    issued_by = models.ForeignKey(
        'UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='warnings_issued'
    )
    
    warning_type = models.CharField(
        max_length=15,
        choices=WarningType.choices
    )
    reason = models.TextField()
    
    # 相关内容
    related_post = models.ForeignKey(
        'Post',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='warnings'
    )
    related_comment = models.ForeignKey(
        'Comment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='warnings'
    )
    
    # 状态
    is_active = models.BooleanField(default=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # 影响
    point_deduction = models.IntegerField(default=0)
    temporary_ban_days = models.IntegerField(
        default=0,
        help_text="临时封禁天数"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'kibbutz_user_warning'
        verbose_name = '用户警告'
        verbose_name_plural = '用户警告'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.display_name} - {self.get_warning_type_display()}"


class UserBan(models.Model):
    """
    用户封禁记录
    
    记录用户的封禁信息。
    """
    
    class BanType(models.TextChoices):
        TEMPORARY = 'temporary', '临时封禁'
        PERMANENT = 'permanent', '永久封禁'
        POSTING_BAN = 'posting_ban', '禁止发帖'
        COMMENT_BAN = 'comment_ban', '禁止评论'
    
    user = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='bans'
    )
    issued_by = models.ForeignKey(
        'UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='bans_issued'
    )
    
    ban_type = models.CharField(
        max_length=20,
        choices=BanType.choices
    )
    reason = models.TextField()
    
    # 时间
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # 相关违规记录
    related_warnings = models.JSONField(
        default=list,
        blank=True,
        help_text="关联的警告ID列表"
    )
    
    is_active = models.BooleanField(default=True)
    lifted_by = models.ForeignKey(
        'UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bans_lifted'
    )
    lifted_at = models.DateTimeField(null=True, blank=True)
    lift_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'kibbutz_user_ban'
        verbose_name = '用户封禁'
        verbose_name_plural = '用户封禁'
        ordering = ['-created_at']
    
    def __str__(self):
        scope = f"至 {self.expires_at}" if self.expires_at else "永久"
        return f"{self.user.display_name} - {self.get_ban_type_display()} ({scope})"
    
    @property
    def is_expired(self):
        """是否已过期"""
        if not self.expires_at:
            return self.ban_type != self.BanType.PERMANENT
        return timezone.now() > self.expires_at


class ModerationService:
    """
    审核服务
    
    提供内容审核的核心逻辑。
    """
    
    # 敏感词检测配置
    SENSITIVE_WORD_CACHE = None
    SENSITIVE_WORD_REGEX = None
    
    @classmethod
    def check_permission(cls, user_profile, action, board=None):
        """
        检查用户权限
        
        Args:
            user_profile: UserProfile 实例
            action: 操作类型
            board: 板块（可选）
        
        Returns:
            bool - 是否有权限
        """
        try:
            moderator = Moderator.objects.get(
                user=user_profile,
                is_active=True
            )
            
            # 超级管理员拥有全部权限
            if moderator.is_super_admin:
                return True
            
            # 检查板块权限
            if board and moderator.board and moderator.board != board:
                return False
            
            # 检查具体权限
            permission_map = {
                'pin': moderator.can_pin,
                'essential': moderator.can_essential,
                'lock': moderator.can_lock,
                'delete': moderator.can_delete,
                'ban': moderator.can_ban,
                'verify_agent': moderator.can_verify_agent,
            }
            
            return permission_map.get(action, False)
            
        except Moderator.DoesNotExist:
            return False
    
    @classmethod
    def moderate_post(cls, moderator, post, action, reason='', request_ip=None):
        """
        执行帖子管理操作
        
        Args:
            moderator: 版主 UserProfile
            post: Post 实例
            action: 操作类型
            reason: 原因
            request_ip: 请求IP
        
        Returns:
            Post 实例
        """
        previous_state = {
            'level': post.level,
            'status': post.status,
        }
        
        if action == 'pin':
            post.level = 'pinned'
        elif action == 'unpin':
            if post.level == 'pinned':
                post.level = 'normal'
        elif action == 'global_pin':
            post.level = 'global_pinned'
        elif action == 'essential':
            post.level = 'essential'
        elif action == 'unessential':
            if post.level == 'essential':
                post.level = 'normal'
        elif action == 'lock':
            post.status = 'locked'
        elif action == 'unlock':
            post.status = 'published'
        elif action == 'delete':
            post.is_deleted = True
            post.status = 'deleted'
        
        post.save()
        
        # 记录日志
        ModerationLog.objects.create(
            moderator=moderator,
            action=action,
            target_type='post',
            target_id=post.id,
            target_author=post.author,
            reason=reason,
            previous_state=previous_state,
            new_state={'level': post.level, 'status': post.status},
            ip_address=request_ip
        )
        
        return post
    
    @classmethod
    def moderate_comment(cls, moderator, comment, action, reason='', request_ip=None):
        """
        执行评论管理操作
        
        Args:
            moderator: 版主 UserProfile
            comment: Comment 实例
            action: 操作类型
            reason: 原因
            request_ip: 请求IP
        
        Returns:
            Comment 实例
        """
        previous_state = {
            'status': comment.status,
        }
        
        if action == 'hide':
            comment.status = 'hidden'
        elif action == 'unhide':
            comment.status = 'visible'
        elif action == 'delete':
            comment.status = 'deleted'
        
        comment.save()
        
        # 记录日志
        ModerationLog.objects.create(
            moderator=moderator,
            action=action,
            target_type='comment',
            target_id=comment.id,
            target_author=comment.author,
            reason=reason,
            previous_state=previous_state,
            new_state={'status': comment.status},
            ip_address=request_ip
        )
        
        return comment
    
    @classmethod
    def check_sensitive_words(cls, content):
        """
        检测敏感词
        
        Args:
            content: 待检测文本
        
        Returns:
            (bool, list) - (是否通过, 发现的敏感词列表)
        """
        if cls.SENSITIVE_WORD_CACHE is None:
            cls._load_sensitive_words()
        
        if not cls.SENSITIVE_WORD_REGEX:
            return True, []
        
        matches = cls.SENSITIVE_WORD_REGEX.findall(content.lower())
        found_words = list(set(matches))
        
        # 检查需要拒绝的内容
        reject_words = SensitiveWord.objects.filter(
            word__in=[w.lower() for w in found_words],
            action=SensitiveWord.Action.REJECT,
            is_active=True
        ).values_list('word', flat=True)
        
        if reject_words:
            return False, list(reject_words)
        
        return True, found_words
    
    @classmethod
    def _load_sensitive_words(cls):
        """加载敏感词库"""
        words = SensitiveWord.objects.filter(
            is_active=True,
            auto_process=True
        ).values_list('word', 'replacement', 'action')
        
        if not words:
            cls.SENSITIVE_WORD_REGEX = re.compile(r'^(?!x)x$')  # 不匹配任何内容
            return
        
        # 构建正则表达式
        word_patterns = []
        for word, replacement, action in words:
            if action != SensitiveWord.Action.REJECT:
                word_patterns.append(re.escape(word))
        
        if word_patterns:
            pattern = '|'.join(word_patterns)
            cls.SENSITIVE_WORD_REGEX = re.compile(pattern, re.IGNORECASE)
        else:
            cls.SENSITIVE_WORD_REGEX = re.compile(r'^(?!x)x$')
    
    @classmethod
    def censor_content(cls, content):
        """
        审核内容，替换敏感词
        
        Args:
            content: 原始内容
        
        Returns:
            str - 审核后的内容
        """
        passed, found_words = cls.check_sensitive_words(content)
        
        if not found_words:
            return content
        
        censored = content
        for word in found_words:
            replacement = '***'
            # 尝试获取配置的替换词
            sw = SensitiveWord.objects.filter(
                word__iexact=word,
                is_active=True
            ).first()
            if sw and sw.replacement:
                replacement = sw.replacement
            
            # 替换（不区分大小写）
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            censored = pattern.sub(replacement, censored)
        
        return censored
    
    @classmethod
    def create_report(cls, reporter, content_type, content_id, 
                     report_type, description, evidence_urls=None):
        """
        创建举报
        
        Args:
            reporter: 举报者 UserProfile
            content_type: 内容类型
            content_id: 内容ID
            report_type: 举报类型
            description: 描述
            evidence_urls: 证据链接
        
        Returns:
            Report 实例
        """
        from .models import Post, Comment
        
        # 获取内容详情
        content_preview = ''
        content_author = None
        
        if content_type == 'post':
            try:
                post = Post.objects.get(id=content_id)
                content_preview = post.content[:500]
                content_author = post.author
            except Post.DoesNotExist:
                pass
        elif content_type == 'comment':
            try:
                comment = Comment.objects.get(id=content_id)
                content_preview = comment.content[:500]
                content_author = comment.author
            except Comment.DoesNotExist:
                pass
        
        # 检查是否重复举报
        existing = Report.objects.filter(
            reporter=reporter,
            content_type=content_type,
            content_id=content_id,
            status__in=['pending', 'reviewing']
        ).first()
        
        if existing:
            return existing
        
        report = Report.objects.create(
            reporter=reporter,
            content_type=content_type,
            content_id=content_id,
            content_author=content_author,
            report_type=report_type,
            content_preview=content_preview,
            description=description,
            evidence_urls=evidence_urls or []
        )
        
        return report
    
    @classmethod
    def handle_report(cls, handler, report, action, resolution):
        """
        处理举报
        
        Args:
            handler: 处理人（版主）
            report: Report 实例
            action: 处理动作 ('resolve', 'dismiss')
            resolution: 处理说明
        
        Returns:
            Report 实例
        """
        if action == 'resolve':
            report.status = Report.ReportStatus.RESOLVED
            
            # 根据举报类型执行相应操作
            if report.report_type == 'spam':
                # 处理垃圾内容
                pass
            elif report.report_type == 'harassment':
                # 处理人身攻击
                pass
        else:
            report.status = Report.ReportStatus.DISMISSED
        
        report.handler = handler
        report.handled_at = timezone.now()
        report.resolution = resolution
        report.save()
        
        return report
    
    @classmethod
    def issue_warning(cls, user, warning_type, reason, issued_by,
                     related_post=None, related_comment=None,
                     point_deduction=0, ban_days=0):
        """
        发出警告
        
        Args:
            user: 被警告用户
            warning_type: 警告类型
            reason: 原因
            issued_by: 发出警告的管理员
            related_post: 关联帖子
            related_comment: 关联评论
            point_deduction: 扣分
            ban_days: 封禁天数
        
        Returns:
            UserWarning 实例
        """
        from .economy import EconomyService
        
        warning = UserWarning.objects.create(
            user=user,
            issued_by=issued_by,
            warning_type=warning_type,
            reason=reason,
            related_post=related_post,
            related_comment=related_comment,
            point_deduction=point_deduction,
            temporary_ban_days=ban_days
        )
        
        # 扣除积分
        if point_deduction > 0:
            EconomyService.deduct_points(
                user_profile=user,
                amount=point_deduction,
                transaction_type='fine',
                description=f'违规警告：{reason[:50]}'
            )
        
        # 临时封禁
        if ban_days > 0:
            ban_expires = timezone.now() + timedelta(days=ban_days)
            UserBan.objects.create(
                user=user,
                issued_by=issued_by,
                ban_type=UserBan.BanType.TEMPORARY,
                reason=reason,
                expires_at=ban_expires,
                related_warnings=[warning.id]
            )
        
        return warning
    
    @classmethod
    def get_pending_reports(cls, limit=20):
        """获取待处理的举报"""
        return Report.objects.filter(
            status=Report.ReportStatus.PENDING
        ).select_related(
            'reporter', 'content_author'
        ).order_by('created_at')[:limit]
    
    @classmethod
    def get_user_violation_count(cls, user_profile, days=30):
        """获取用户近期违规次数"""
        start_date = timezone.now() - timedelta(days=days)
        return UserWarning.objects.filter(
            user=user_profile,
            created_at__gte=start_date
        ).count()


# 导入 Post 和 Comment（避免循环引用）
from .models import Post, Comment

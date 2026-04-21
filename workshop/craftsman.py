# -*- coding: utf-8 -*-
"""
Workshop 工匠认证核心模块
Neshama Agent 项目 - 工匠认证、等级晋升、特权与惩戒体系
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import timedelta
import hashlib
import json


class ApplicationStatus(Enum):
    """申请状态枚举"""
    PENDING = 'pending', '待审核'
    APPROVED = 'approved', '已通过'
    REJECTED = 'rejected', '已拒绝'
    CANCELLED = 'cancelled', '已取消'


class PunishmentType(Enum):
    """惩罚类型枚举"""
    WARNING = 'warning', '警告'
    SCORE_DEDUCTION = 'score_deduction', '扣分'
    DEMOTION = 'demotion', '降级'
    SUSPENSION = 'suspension', '暂停权限'
    BAN = 'ban', '封禁'


@dataclass
class LevelRequirement:
    """等级要求配置"""
    level_name: str
    min_skills: int
    min_installs: int
    min_rating: float
    min_revenue: float = 0.0
    min_active_days: int = 0
    badges_required: List[str] = field(default_factory=list)


class LevelConfig:
    """等级配置"""
    
    # 等级晋升要求
    REQUIREMENTS = {
        'novice': LevelRequirement(
            level_name='novice',
            min_skills=0,
            min_installs=0,
            min_rating=0.0,
            min_active_days=0
        ),
        'skilled': LevelRequirement(
            level_name='skilled',
            min_skills=3,
            min_installs=50,
            min_rating=4.0,
            min_active_days=30
        ),
        'master': LevelRequirement(
            level_name='master',
            min_skills=10,
            min_installs=500,
            min_rating=4.5,
            min_active_days=90,
            badges_required=['quality_certified']
        ),
        'legend': LevelRequirement(
            level_name='legend',
            min_skills=30,
            min_installs=5000,
            min_rating=4.8,
            min_revenue=10000.0,
            min_active_days=365,
            badges_required=['quality_certified', 'innovation_award', 'top_seller']
        ),
    }
    
    # 各等级特权
    PRIVILEGES = {
        'novice': {
            'max_skills': 5,
            'can_monetize': False,
            'commission_rate': 0.7,
            'featured_slot': 0,
            'analytics_basic': True,
            'priority_support': False,
            'custom_branding': False,
        },
        'skilled': {
            'max_skills': 20,
            'can_monetize': True,
            'commission_rate': 0.65,
            'featured_slot': 1,
            'analytics_basic': True,
            'analytics_advanced': False,
            'priority_support': False,
            'custom_branding': False,
        },
        'master': {
            'max_skills': 100,
            'can_monetize': True,
            'commission_rate': 0.60,
            'featured_slot': 3,
            'analytics_basic': True,
            'analytics_advanced': True,
            'priority_support': True,
            'custom_branding': True,
        },
        'legend': {
            'max_skills': float('inf'),
            'can_monetize': True,
            'commission_rate': 0.55,
            'featured_slot': 5,
            'analytics_basic': True,
            'analytics_advanced': True,
            'priority_support': True,
            'custom_branding': True,
            'beta_features': True,
        },
    }
    
    @classmethod
    def get_privileges(cls, level: str) -> Dict:
        """获取等级特权"""
        return cls.PRIVILEGES.get(level, cls.PRIVILEGES['novice'])
    
    @classmethod
    def get_requirement(cls, level: str) -> LevelRequirement:
        """获取等级要求"""
        return cls.REQUIREMENTS.get(level)
    
    @classmethod
    def get_next_level(cls, current_level: str) -> Optional[str]:
        """获取下一等级"""
        level_order = ['novice', 'skilled', 'master', 'legend']
        try:
            current_idx = level_order.index(current_level)
            if current_idx < len(level_order) - 1:
                return level_order[current_idx + 1]
        except ValueError:
            pass
        return None


class CraftsmanApplication(models.Model):
    """工匠认证申请表"""
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='craftsman_applications',
                             verbose_name='申请人')
    status = models.CharField(max_length=20, 
                              choices=[(s.value, s.label) for s in ApplicationStatus],
                              default=ApplicationStatus.PENDING.value,
                              verbose_name='申请状态')
    
    # 基本信息
    real_name = models.CharField(max_length=50, verbose_name='真实姓名')
    id_number = models.CharField(max_length=20, blank=True, verbose_name='身份证号')
    phone = models.CharField(max_length=20, verbose_name='联系电话')
    portfolio_url = models.URLField(blank=True, verbose_name='作品集链接')
    
    # 专业背景
    expertise_areas = models.JSONField(default=list, verbose_name='擅长领域')
    years_experience = models.IntegerField(default=0, verbose_name='从业年限')
    certifications = models.JSONField(default=list, verbose_name='相关证书')
    
    # 审核信息
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name='reviewed_applications',
                                    verbose_name='审核人')
    review_notes = models.TextField(blank=True, verbose_name='审核备注')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    
    # 申请材料
    id_card_front = models.URLField(blank=True, verbose_name='身份证正面')
    id_card_back = models.URLField(blank=True, verbose_name='身份证背面')
    portfolio_files = models.JSONField(default=list, verbose_name='作品文件列表')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='申请时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'workshop_craftsman_application'
        verbose_name = '工匠申请'
        verbose_name_plural = '工匠申请'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"
    
    def approve(self, reviewer: User, notes: str = ''):
        """审核通过"""
        from .models import CreatorProfile, CraftsmanLevel
        
        self.status = ApplicationStatus.APPROVED.value
        self.reviewed_by = reviewer
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.save()
        
        # 创建工匠档案
        profile, created = CreatorProfile.objects.get_or_create(
            user=self.user,
            defaults={
                'level': CraftsmanLevel.NOVICE,
                'title': '新手工匠',
            }
        )
        if not created:
            profile.title = '新手工匠'
            profile.save()
        
        return profile
    
    def reject(self, reviewer: User, reason: str):
        """审核拒绝"""
        self.status = ApplicationStatus.REJECTED.value
        self.reviewed_by = reviewer
        self.review_notes = reason
        self.reviewed_at = timezone.now()
        self.save()


class CraftsmanBadge(models.Model):
    """工匠徽章模型"""
    name = models.CharField(max_length=50, unique=True, verbose_name='徽章名称')
    slug = models.SlugField(max_length=50, unique=True, verbose_name='徽章标识')
    description = models.TextField(verbose_name='徽章说明')
    icon = models.URLField(verbose_name='徽章图标')
    badge_type = models.CharField(max_length=30, verbose_name='徽章类型')
    
    # 获取条件
    condition_type = models.CharField(max_length=30, verbose_name='条件类型')
    condition_value = models.JSONField(default=dict, verbose_name='条件值')
    
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    rarity = models.IntegerField(default=1, verbose_name='稀有度(1-5)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workshop_craftsman_badge'
        verbose_name = '工匠徽章'
        verbose_name_plural = '工匠徽章'

    def __str__(self):
        return self.name


class CraftsmanBadgeEarned(models.Model):
    """工匠徽章获得记录"""
    craftsman = models.ForeignKey('CreatorProfile', on_delete=models.CASCADE,
                                  related_name='earned_badges',
                                  verbose_name='工匠')
    badge = models.ForeignKey(CraftsmanBadge, on_delete=models.CASCADE,
                              related_name='earnings',
                              verbose_name='徽章')
    earned_at = models.DateTimeField(auto_now_add=True, verbose_name='获得时间')
    source = models.CharField(max_length=100, blank=True, verbose_name='获得来源')

    class Meta:
        db_table = 'workshop_badge_earned'
        verbose_name = '徽章获得记录'
        verbose_name_plural = '徽章获得记录'
        unique_together = [['craftsman', 'badge']]

    def __str__(self):
        return f"{self.craftsman} earned {self.badge.name}"


class CraftsmanPunishment(models.Model):
    """工匠惩戒记录"""
    craftsman = models.ForeignKey('CreatorProfile', on_delete=models.CASCADE,
                                 related_name='punishments',
                                 verbose_name='工匠')
    punishment_type = models.CharField(max_length=20,
                                       choices=[(p.value, p.label) for p in PunishmentType],
                                       verbose_name='惩罚类型')
    reason = models.TextField(verbose_name='惩罚原因')
    evidence = models.JSONField(default=list, verbose_name='证据材料')
    
    # 惩罚详情
    score_deducted = models.IntegerField(default=0, verbose_name='扣减分数')
    demotion_to = models.CharField(max_length=20, blank=True, verbose_name='降级至')
    suspension_days = models.IntegerField(default=0, verbose_name='暂停天数')
    
    # 处理信息
    handled_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, related_name='handled_punishments',
                                   verbose_name='处理人')
    is_active = models.BooleanField(default=True, verbose_name='是否生效')
    is_appealed = models.BooleanField(default=False, verbose_name='是否申诉')
    appeal_result = models.TextField(blank=True, verbose_name='申诉结果')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='过期时间')

    class Meta:
        db_table = 'workshop_craftsman_punishment'
        verbose_name = '工匠惩戒'
        verbose_name_plural = '工匠惩戒'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.craftsman} - {self.get_punishment_type_display()}"
    
    def apply_punishment(self):
        """执行惩罚"""
        profile = self.craftsman
        
        if self.punishment_type == PunishmentType.WARNING.value:
            # 警告只是记录
            pass
        
        elif self.punishment_type == PunishmentType.SCORE_DEDUCTION.value:
            profile.credibility_score = max(0, profile.credibility_score - self.score_deducted)
            profile.save()
        
        elif self.punishment_type == PunishmentType.DEMOTION.value:
            if self.demotion_to:
                profile.level = self.demotion_to
                profile.save()
                # 更新称号
                titles = {
                    'novice': '新手工匠',
                    'skilled': '熟练工匠', 
                    'master': '大师工匠',
                }
                profile.title = titles.get(self.demotion_to, profile.title)
                profile.save()
        
        elif self.punishment_type == PunishmentType.SUSPENSION.value:
            profile.is_suspended = True
            profile.suspension_until = self.expires_at
            profile.save()
        
        elif self.punishment_type == PunishmentType.BAN.value:
            profile.is_banned = True
            profile.ban_reason = self.reason
            profile.save()
        
        self.is_active = True
        self.save()


class CraftsmanLevelManager:
    """
    工匠等级管理器
    
    负责：
    - 自动检查等级晋升
    - 等级调整
    - 权益计算
    """
    
    def __init__(self, craftsman_profile):
        self.profile = craftsman_profile
    
    def check_auto_promotion(self) -> Dict:
        """
        检查是否满足自动晋升条件
        
        Returns:
            Dict: 包含是否可晋升、原因等信息的字典
        """
        current_level = self.profile.level
        next_level = LevelConfig.get_next_level(current_level)
        
        if not next_level:
            return {
                'can_promote': False,
                'reason': '已达到最高等级',
                'is_max_level': True
            }
        
        requirement = LevelConfig.get_requirement(next_level)
        if not requirement:
            return {'can_promote': False, 'reason': '配置错误'}
        
        # 计算工匠当前数据
        stats = self.get_stats()
        
        # 检查各项指标
        checks = {
            'min_skills': stats['skills_count'] >= requirement.min_skills,
            'min_installs': stats['total_installs'] >= requirement.min_installs,
            'min_rating': stats['avg_rating'] >= requirement.min_rating,
            'min_active_days': stats['active_days'] >= requirement.min_active_days,
        }
        
        # 传奇等级额外检查收入
        if next_level == 'legend':
            checks['min_revenue'] = stats['total_revenue'] >= requirement.min_revenue
        
        # 检查所需徽章
        has_required_badges = True
        if requirement.badges_required:
            earned_badges = self.profile.earned_badges.values_list('badge__slug', flat=True)
            has_required_badges = all(b in earned_badges for b in requirement.badges_required)
        checks['badges'] = has_required_badges
        
        can_promote = all(checks.values())
        
        failed_checks = [k for k, v in checks.items() if not v]
        
        return {
            'can_promote': can_promote,
            'next_level': next_level,
            'checks': checks,
            'failed_checks': failed_checks,
            'stats': stats,
            'requirement': {
                'min_skills': requirement.min_skills,
                'min_installs': requirement.min_installs,
                'min_rating': requirement.min_rating,
                'min_active_days': requirement.min_active_days,
                'min_revenue': requirement.min_revenue,
                'badges_required': requirement.badges_required,
            }
        }
    
    def promote(self, level: str, reason: str = '', operator: User = None) -> bool:
        """
        晋升工匠等级
        
        Args:
            level: 目标等级
            reason: 晋升原因
            operator: 操作人
            
        Returns:
            bool: 是否成功
        """
        level_titles = {
            'novice': '新手工匠',
            'skilled': '熟练工匠',
            'master': '大师工匠',
            'legend': '传奇工匠',
        }
        
        old_level = self.profile.level
        if level not in level_titles:
            return False
        
        self.profile.level = level
        self.profile.title = level_titles[level]
        self.profile.save()
        
        # 记录晋升历史
        LevelUpHistory.objects.create(
            craftsman=self.profile,
            old_level=old_level,
            new_level=level,
            reason=reason,
            operator=operator,
            is_auto=True
        )
        
        return True
    
    def demote(self, level: str, reason: str, operator: User) -> bool:
        """降级工匠"""
        level_titles = {
            'novice': '新手工匠',
            'skilled': '熟练工匠',
            'master': '大师工匠',
        }
        
        if level not in level_titles:
            return False
        
        old_level = self.profile.level
        
        self.profile.level = level
        self.profile.title = level_titles[level]
        self.profile.save()
        
        # 记录降级历史
        LevelUpHistory.objects.create(
            craftsman=self.profile,
            old_level=old_level,
            new_level=level,
            reason=reason,
            operator=operator,
            is_auto=False
        )
        
        return True
    
    def get_stats(self) -> Dict:
        """获取工匠统计数据"""
        from .models import Skill, SkillStatus, InstallRecord, Rating
        
        skills = Skill.objects.filter(
            creator=self.profile,
            status=SkillStatus.APPROVED
        )
        
        stats = {
            'skills_count': skills.count(),
            'total_installs': InstallRecord.objects.filter(skill__creator=self.profile).count(),
            'avg_rating': self.profile.avg_rating,
            'active_days': (timezone.now() - self.profile.created_at).days,
            'total_revenue': getattr(self.profile, 'total_revenue', 0),
        }
        
        return stats
    
    def get_privileges(self) -> Dict:
        """获取当前特权"""
        return LevelConfig.get_privileges(self.profile.level)
    
    def can_submit_skill(self) -> Tuple[bool, str]:
        """检查是否可以提交技能"""
        privileges = self.get_privileges()
        stats = self.get_stats()
        
        if stats['skills_count'] >= privileges['max_skills']:
            return False, f"已达到技能数量上限({privileges['max_skills']}个)"
        
        if self.profile.is_suspended:
            return False, f"账号被暂停，暂停至{self.profile.suspension_until}"
        
        if self.profile.is_banned:
            return False, "账号已被封禁"
        
        return True, "可以提交"
    
    def check_demotion_conditions(self) -> List[Dict]:
        """
        检查是否需要降级
        
        Returns:
            List[Dict]: 触发降级的条件列表
        """
        from .models import SkillStatus
        
        demotion_triggers = []
        
        # 检查技能质量
        low_quality_count = Skill.objects.filter(
            creator=self.profile,
            status=SkillStatus.APPROVED,
            avg_rating__lt=3.0
        ).count()
        
        if low_quality_count >= 5:
            demotion_triggers.append({
                'reason': f'低质量技能过多({low_quality_count}个评分低于3.0)',
                'suggested_level': self._get_demotion_level()
            })
        
        # 检查违规记录
        recent_punishments = CraftsmanPunishment.objects.filter(
            craftsman=self.profile,
            punishment_type__in=[PunishmentType.DEMOTION.value, PunishmentType.BAN.value],
            created_at__gte=timezone.now() - timedelta(days=180)
        ).count()
        
        if recent_punishments >= 2:
            demotion_triggers.append({
                'reason': f'半年内累计{recent_punishments}次严重违规',
                'suggested_level': self._get_demotion_level()
            })
        
        # 检查长期不活跃
        latest_skill = Skill.objects.filter(
            creator=self.profile
        ).order_by('-updated_at').first()
        
        if latest_skill:
            inactive_days = (timezone.now() - latest_skill.updated_at).days
            if inactive_days > 365 and self.profile.level in ['skilled', 'master']:
                demotion_triggers.append({
                    'reason': f'超过一年未更新技能({inactive_days}天)',
                    'suggested_level': 'novice'
                })
        
        return demotion_triggers
    
    def _get_demotion_level(self) -> str:
        """获取应降级到的等级"""
        level_order = ['novice', 'skilled', 'master', 'legend']
        try:
            current_idx = level_order.index(self.profile.level)
            if current_idx > 0:
                return level_order[current_idx - 1]
        except ValueError:
            pass
        return 'novice'


class LevelUpHistory(models.Model):
    """等级变动历史"""
    craftsman = models.ForeignKey('CreatorProfile', on_delete=models.CASCADE,
                                  related_name='level_history',
                                  verbose_name='工匠')
    old_level = models.CharField(max_length=20, verbose_name='原等级')
    new_level = models.CharField(max_length=20, verbose_name='新等级')
    reason = models.CharField(max_length=200, verbose_name='变动原因')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL,
                                 null=True, related_name='level_changes',
                                 verbose_name='操作人')
    is_auto = models.BooleanField(default=True, verbose_name='是否自动')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='变动时间')

    class Meta:
        db_table = 'workshop_level_history'
        verbose_name = '等级变动历史'
        verbose_name_plural = '等级变动历史'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.craftsman}: {self.old_level} -> {self.new_level}"


class Invitation(models.Model):
    """邀请关系模型"""
    inviter = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='sent_invitations',
                                verbose_name='邀请人')
    invitee = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='received_invitations',
                                verbose_name='被邀请人')
    invite_code = models.CharField(max_length=20, unique=True, verbose_name='邀请码')
    bonus_granted = models.BooleanField(default=False, verbose_name='奖励是否发放')
    bonus_amount = models.IntegerField(default=0, verbose_name='奖励金额')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='邀请时间')
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name='接受时间')

    class Meta:
        db_table = 'workshop_invitation'
        verbose_name = '邀请关系'
        verbose_name_plural = '邀请关系'
        unique_together = [['inviter', 'invitee']]

    def __str__(self):
        return f"{self.inviter.username} -> {self.invitee.username}"
    
    @classmethod
    def generate_code(cls) -> str:
        """生成唯一邀请码"""
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not cls.objects.filter(invite_code=code).exists():
                return code


class SkillChallenge(models.Model):
    """技能挑战赛模型"""
    title = models.CharField(max_length=100, verbose_name='挑战赛标题')
    description = models.TextField(verbose_name='挑战赛描述')
    category = models.ForeignKey('SkillCategory', on_delete=models.SET_NULL,
                                null=True, related_name='challenges',
                                verbose_name='所属分类')
    
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间')
    judging_time = models.DateTimeField(verbose_name='评审时间')
    
    # 奖励配置
    prizes = models.JSONField(default=dict, verbose_name='奖励配置')
    entry_fee = models.IntegerField(default=0, verbose_name='报名费')
    max_entries = models.IntegerField(default=0, verbose_name='最大参赛人数')
    
    # 评审标准
    criteria = models.JSONField(default=list, verbose_name='评审标准')
    
    is_active = models.BooleanField(default=True, verbose_name='是否进行中')
    winner_count = models.IntegerField(default=3, verbose_name='获奖人数')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'workshop_skill_challenge'
        verbose_name = '技能挑战赛'
        verbose_name_plural = '技能挑战赛'
        ordering = ['-start_time']

    def __str__(self):
        return self.title
    
    def is_ongoing(self) -> bool:
        """检查是否正在进行"""
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time


class ChallengeEntry(models.Model):
    """挑战赛参赛记录"""
    challenge = models.ForeignKey(SkillChallenge, on_delete=models.CASCADE,
                                   related_name='entries',
                                   verbose_name='挑战赛')
    participant = models.ForeignKey(User, on_delete=models.CASCADE,
                                     related_name='challenge_entries',
                                     verbose_name='参赛者')
    skill = models.ForeignKey('Skill', on_delete=models.CASCADE,
                             related_name='challenge_entries',
                             verbose_name='参赛技能')
    
    # 评审结果
    scores = models.JSONField(default=dict, verbose_name='各项得分')
    total_score = models.DecimalField(max_digits=5, decimal_places=2,
                                       default=0, verbose_name='总分')
    rank = models.IntegerField(default=0, verbose_name='排名')
    is_winner = models.BooleanField(default=False, verbose_name='是否获奖')
    prize_received = models.BooleanField(default=False, verbose_name='奖励是否发放')
    
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name='提交时间')
    judged_at = models.DateTimeField(null=True, blank=True, verbose_name='评审时间')

    class Meta:
        db_table = 'workshop_challenge_entry'
        verbose_name = '挑战赛参赛'
        verbose_name_plural = '挑战赛参赛'
        unique_together = [['challenge', 'participant', 'skill']]

    def __str__(self):
        return f"{self.challenge.title} - {self.participant.username}"
    
    def calculate_total_score(self):
        """计算总分"""
        if self.scores:
            self.total_score = sum(self.scores.values())
            self.save(update_fields=['total_score'])

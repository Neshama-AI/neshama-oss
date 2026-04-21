# -*- coding: utf-8 -*-
"""
Workshop 技能市场数据模型
Neshama Agent 项目 - 工匠认证技能交易平台
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class CraftsmanLevel(models.TextChoices):
    """工匠等级枚举"""
    NOVICE = 'novice', '新手工匠'
    SKILLED = 'skilled', '熟练工匠'
    MASTER = 'master', '大师工匠'
    LEGEND = 'legend', '传奇工匠'


class SkillStatus(models.TextChoices):
    """技能审核状态枚举"""
    DRAFT = 'draft', '草稿'
    PENDING = 'pending', '待审核'
    APPROVED = 'approved', '已通过'
    REJECTED = 'rejected', '已拒绝'
    BANNED = 'banned', '已封禁'


class SkillCategory(models.Model):
    """技能分类模型"""
    name = models.CharField(max_length=50, verbose_name='分类名称')
    slug = models.SlugField(max_length=50, unique=True, verbose_name='URL别名')
    description = models.TextField(blank=True, verbose_name='分类描述')
    icon = models.CharField(max_length=100, blank=True, verbose_name='图标类名')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='children',
                               verbose_name='父分类')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workshop_category'
        verbose_name = '技能分类'
        verbose_name_plural = '技能分类'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def get_full_path(self):
        """获取完整分类路径"""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name


class CreatorProfile(models.Model):
    """创作者/工匠资料模型"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, 
                                 related_name='craftsman_profile',
                                 verbose_name='关联用户')
    level = models.CharField(max_length=20, choices=CraftsmanLevel.choices,
                             default=CraftsmanLevel.NOVICE, verbose_name='工匠等级')
    title = models.CharField(max_length=100, blank=True, verbose_name='称号')
    bio = models.TextField(blank=True, verbose_name='个人简介')
    avatar = models.URLField(blank=True, verbose_name='头像URL')
    skills_count = models.IntegerField(default=0, verbose_name='技能总数')
    total_installs = models.IntegerField(default=0, verbose_name='总安装量')
    total_ratings = models.IntegerField(default=0, verbose_name='总评分数')
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, 
                                     default=0, verbose_name='平均评分')
    verified = models.BooleanField(default=False, verbose_name='是否认证')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workshop_creator'
        verbose_name = '创作者资料'
        verbose_name_plural = '创作者资料'

    def __str__(self):
        return f"{self.user.username} ({self.get_level_display()})"

    def update_stats(self):
        """更新统计数据"""
        skills = self.skills.filter(status=SkillStatus.APPROVED)
        self.skills_count = skills.count()
        self.total_installs = InstallRecord.objects.filter(
            skill__creator=self
        ).count()
        ratings = Rating.objects.filter(skill__creator=self)
        self.total_ratings = ratings.count()
        if self.total_ratings > 0:
            self.avg_rating = sum(r.rating for r in ratings) / self.total_ratings
        else:
            self.avg_rating = 0
        self.save()

    def check_level_up(self):
        """检查是否满足等级提升条件"""
        # 新手 -> 熟练: 3个通过技能 + 50安装量 + 4.0评分
        if self.level == CraftsmanLevel.NOVICE:
            if self.skills_count >= 3 and self.total_installs >= 50 and self.avg_rating >= 4.0:
                self.level = CraftsmanLevel.SKILLED
                self.title = '熟练工匠'
                self.save()
        # 熟练 -> 大师: 10个通过技能 + 500安装量 + 4.5评分
        elif self.level == CraftsmanLevel.SKILLED:
            if self.skills_count >= 10 and self.total_installs >= 500 and self.avg_rating >= 4.5:
                self.level = CraftsmanLevel.MASTER
                self.title = '大师工匠'
                self.save()


class Skill(models.Model):
    """技能模型"""
    creator = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE,
                                  related_name='skills', verbose_name='创作者')
    category = models.ForeignKey(SkillCategory, on_delete=models.SET_NULL,
                                  null=True, related_name='skills',
                                  verbose_name='所属分类')
    name = models.CharField(max_length=100, verbose_name='技能名称')
    slug = models.SlugField(max_length=120, verbose_name='URL别名')
    short_description = models.CharField(max_length=200, verbose_name='简短描述')
    full_description = models.TextField(verbose_name='完整描述')
    icon = models.URLField(blank=True, verbose_name='图标URL')
    preview_images = models.JSONField(default=list, blank=True, 
                                       verbose_name='预览图片列表')
    tags = models.JSONField(default=list, blank=True, verbose_name='标签')
    
    status = models.CharField(max_length=20, choices=SkillStatus.choices,
                              default=SkillStatus.DRAFT, verbose_name='审核状态')
    reject_reason = models.TextField(blank=True, verbose_name='拒绝原因')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name='reviewed_skills',
                                    verbose_name='审核人')
    
    install_count = models.IntegerField(default=0, verbose_name='安装量')
    rating_count = models.IntegerField(default=0, verbose_name='评分数')
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, 
                                     default=0, verbose_name='平均评分')
    
    is_featured = models.BooleanField(default=False, verbose_name='是否精选')
    is_premium = models.BooleanField(default=False, verbose_name='是否付费')
    price = models.DecimalField(max_digits=10, decimal_places=2, 
                                default=0, verbose_name='价格')
    
    version = models.CharField(max_length=20, default='1.0.0', verbose_name='当前版本')
    min_app_version = models.CharField(max_length=20, blank=True, 
                                       verbose_name='最低应用版本')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='发布时间')

    class Meta:
        db_table = 'workshop_skill'
        verbose_name = '技能'
        verbose_name_plural = '技能'
        ordering = ['-created_at']
        unique_together = [['creator', 'slug']]

    def __str__(self):
        return f"{self.name} by {self.creator}"

    def submit_for_review(self):
        """提交审核"""
        if self.status == SkillStatus.DRAFT:
            self.status = SkillStatus.PENDING
            self.save()
            ReviewRequest.objects.create(skill=self)
            return True
        return False

    def approve(self, reviewer):
        """审核通过"""
        self.status = SkillStatus.APPROVED
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.published_at = timezone.now()
        self.save()
        self.creator.update_stats()
        self.creator.check_level_up()

    def reject(self, reviewer, reason):
        """审核拒绝"""
        self.status = SkillStatus.REJECTED
        self.reject_reason = reason
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.save()


class SkillVersion(models.Model):
    """技能版本模型"""
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE,
                               related_name='versions', verbose_name='所属技能')
    version = models.CharField(max_length=20, verbose_name='版本号')
    changelog = models.TextField(verbose_name='更新日志')
    file_url = models.URLField(verbose_name='文件URL')
    file_size = models.BigIntegerField(default=0, verbose_name='文件大小(字节)')
    md5_hash = models.CharField(max_length=64, blank=True, verbose_name='MD5校验')
    
    status = models.CharField(max_length=20, choices=SkillStatus.choices,
                              default=SkillStatus.PENDING, verbose_name='审核状态')
    is_stable = models.BooleanField(default=True, verbose_name='是否稳定版')
    
    install_count = models.IntegerField(default=0, verbose_name='该版本安装量')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workshop_skill_version'
        verbose_name = '技能版本'
        verbose_name_plural = '技能版本'
        ordering = ['-created_at']
        unique_together = [['skill', 'version']]

    def __str__(self):
        return f"{self.skill.name} v{self.version}"


class ReviewRequest(models.Model):
    """审核请求模型"""
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE,
                              related_name='review_requests',
                              verbose_name='技能')
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL,
                                  null=True, related_name='assigned_reviews',
                                  verbose_name='分配审核员')
    notes = models.TextField(blank=True, verbose_name='审核备注')
    is_automated = models.BooleanField(default=True, verbose_name='是否自动审核')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workshop_review_request'
        verbose_name = '审核请求'
        verbose_name_plural = '审核请求'

    def __str__(self):
        return f"Review for {self.skill.name}"


class Rating(models.Model):
    """评分模型"""
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE,
                               related_name='ratings', verbose_name='技能')
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='skill_ratings', verbose_name='评分用户')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)],
                                 verbose_name='评分')
    comment = models.TextField(blank=True, verbose_name='评价内容')
    is_anonymous = models.BooleanField(default=False, verbose_name='是否匿名')
    is_verified = models.BooleanField(default=False, verbose_name='是否已安装用户')
    
    helpful_count = models.IntegerField(default=0, verbose_name='有帮助数')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workshop_rating'
        verbose_name = '评分'
        verbose_name_plural = '评分'
        unique_together = [['skill', 'user']]

    def __str__(self):
        return f"{self.user.username} rated {self.skill.name} {self.rating}★"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_skill_rating()

    def update_skill_rating(self):
        """更新技能平均评分"""
        ratings = Rating.objects.filter(skill=self.skill)
        count = ratings.count()
        avg = sum(r.rating for r in ratings) / count if count > 0 else 0
        self.skill.rating_count = count
        self.skill.avg_rating = avg
        self.skill.save(update_fields=['rating_count', 'avg_rating'])


class InstallRecord(models.Model):
    """安装记录模型"""
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE,
                              related_name='install_records',
                              verbose_name='技能')
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='installed_skills',
                             verbose_name='安装用户')
    version = models.CharField(max_length=20, verbose_name='安装版本')
    
    source = models.CharField(max_length=50, default='marketplace',
                              verbose_name='安装来源')
    device_info = models.JSONField(default=dict, blank=True,
                                   verbose_name='设备信息')
    
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')
    last_used = models.DateTimeField(null=True, blank=True, 
                                      verbose_name='最后使用时间')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workshop_install_record'
        verbose_name = '安装记录'
        verbose_name_plural = '安装记录'
        unique_together = [['skill', 'user']]

    def __str__(self):
        return f"{self.user.username} installed {self.skill.name}"


class Favorite(models.Model):
    """收藏模型"""
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE,
                              related_name='favorites', verbose_name='技能')
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='favorite_skills',
                             verbose_name='收藏用户')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workshop_favorite'
        verbose_name = '收藏'
        verbose_name_plural = '收藏'
        unique_together = [['skill', 'user']]

    def __str__(self):
        return f"{self.user.username} favorited {self.skill.name}"

# -*- coding: utf-8 -*-
"""
Workshop API 序列化器
Neshama Agent 项目 - REST API 数据转换
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Skill, SkillCategory, SkillVersion, CreatorProfile,
    Rating, InstallRecord, Favorite, ReviewRequest
)
from .review import AutomatedReviewer, QualityScoreCalculator


class UserBasicSerializer(serializers.ModelSerializer):
    """用户基本信息序列化器"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class CreatorProfileSerializer(serializers.ModelSerializer):
    """创作者资料序列化器"""
    user = UserBasicSerializer(read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    
    class Meta:
        model = CreatorProfile
        fields = [
            'id', 'user', 'level', 'level_display', 'title', 'bio',
            'avatar', 'skills_count', 'total_installs', 'total_ratings',
            'avg_rating', 'verified', 'created_at'
        ]
        read_only_fields = [
            'skills_count', 'total_installs', 'total_ratings', 'avg_rating'
        ]


class CreatorPublicSerializer(serializers.ModelSerializer):
    """公开的创作者信息（精简版）"""
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = CreatorProfile
        fields = [
            'id', 'username', 'level', 'level_display', 'title',
            'avatar', 'skills_count', 'avg_rating', 'verified'
        ]


class SkillCategorySerializer(serializers.ModelSerializer):
    """技能分类序列化器"""
    children = serializers.SerializerMethodField()
    skill_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SkillCategory
        fields = [
            'id', 'name', 'slug', 'description', 'icon',
            'parent', 'children', 'skill_count', 'sort_order'
        ]
    
    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return SkillCategorySerializer(children, many=True).data
    
    def get_skill_count(self, obj):
        return obj.skills.filter(status='approved').count()


class SkillVersionSerializer(serializers.ModelSerializer):
    """技能版本序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SkillVersion
        fields = [
            'id', 'version', 'changelog', 'file_url', 'file_size',
            'status', 'status_display', 'is_stable', 'install_count',
            'created_at'
        ]
        read_only_fields = ['status', 'install_count', 'created_at']


class RatingSerializer(serializers.ModelSerializer):
    """评分序列化器"""
    username = serializers.CharField(source='user.username', read_only=True)
    is_anonymous = serializers.BooleanField(write_only=True, default=False)
    
    class Meta:
        model = Rating
        fields = [
            'id', 'user', 'username', 'rating', 'comment',
            'is_anonymous', 'is_verified', 'helpful_count', 'created_at'
        ]
        read_only_fields = ['user', 'is_verified', 'helpful_count', 'created_at']
    
    def create(self, validated_data):
        # 如果是匿名评分，不显示用户名
        is_anonymous = validated_data.pop('is_anonymous', False)
        validated_data['is_anonymous'] = is_anonymous
        return super().create(validated_data)


class SkillListSerializer(serializers.ModelSerializer):
    """技能列表序列化器（精简版）"""
    creator = CreatorPublicSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    quality_score = serializers.SerializerMethodField()
    
    class Meta:
        model = Skill
        fields = [
            'id', 'name', 'slug', 'short_description', 'icon',
            'creator', 'category', 'category_name', 'status', 'status_display',
            'install_count', 'rating_count', 'avg_rating', 'is_featured',
            'is_premium', 'price', 'version', 'quality_score', 'created_at'
        ]
    
    def get_quality_score(self, obj):
        # 动态计算质量分数
        try:
            return QualityScoreCalculator.calculate(obj)['total_score']
        except:
            return 0


class SkillDetailSerializer(serializers.ModelSerializer):
    """技能详情序列化器（完整版）"""
    creator = CreatorProfileSerializer(read_only=True)
    category = SkillCategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False)
    versions = SkillVersionSerializer(many=True, read_only=True)
    recent_ratings = serializers.SerializerMethodField()
    is_installed = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    quality_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Skill
        fields = [
            'id', 'name', 'slug', 'short_description', 'full_description',
            'icon', 'preview_images', 'tags',
            'creator', 'category', 'category_id',
            'status', 'status_display', 'reject_reason', 'reviewed_at',
            'install_count', 'rating_count', 'avg_rating',
            'is_featured', 'is_premium', 'price',
            'version', 'min_app_version',
            'versions', 'recent_ratings',
            'is_installed', 'is_favorited', 'quality_info',
            'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = [
            'status', 'reject_reason', 'reviewed_at', 'reviewed_by',
            'install_count', 'rating_count', 'avg_rating', 'created_at',
            'updated_at', 'published_at'
        ]
    
    def get_recent_ratings(self, obj):
        ratings = obj.ratings.filter(is_anonymous=False)[:5]
        return RatingSerializer(ratings, many=True).data
    
    def get_is_installed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.install_records.filter(user=request.user, is_active=True).exists()
        return False
    
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False
    
    def get_quality_info(self, obj):
        try:
            return QualityScoreCalculator.calculate(obj)
        except:
            return None
    
    def create(self, validated_data):
        validated_data.pop('category_id', None)
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        category_id = validated_data.pop('category_id', None)
        if category_id:
            instance.category_id = category_id
        return super().update(instance, validated_data)


class SkillCreateSerializer(serializers.ModelSerializer):
    """技能创建序列化器"""
    review_items = serializers.SerializerMethodField()
    
    class Meta:
        model = Skill
        fields = [
            'id', 'name', 'slug', 'short_description', 'full_description',
            'icon', 'preview_images', 'tags', 'category',
            'is_premium', 'price', 'version', 'min_app_version',
            'review_items'
        ]
    
    def get_review_items(self, obj):
        # 返回审核项预览
        reviewer = AutomatedReviewer(obj)
        _, items = reviewer.run_all_checks()
        return [
            {
                'name': item.name,
                'status': item.status.value,
                'message': item.message
            }
            for item in items
        ]
    
    def validate_slug(self, value):
        """验证slug唯一性"""
        user = self.context['request'].user
        creator = user.craftsman_profile
        
        existing = Skill.objects.filter(
            creator=creator,
            slug=value
        ).exclude(id=self.instance.id if self.instance else None)
        
        if existing.exists():
            raise serializers.ValidationError('该URL别名已被使用')
        
        return value
    
    def validate(self, attrs):
        # 检查是否付费技能
        if attrs.get('is_premium') and not attrs.get('price'):
            attrs['price'] = 0
        return attrs
    
    def create(self, validated_data):
        # 关联当前用户为创作者
        user = self.context['request'].user
        validated_data['creator'] = user.craftsman_profile
        return super().create(validated_data)


class InstallRecordSerializer(serializers.ModelSerializer):
    """安装记录序列化器"""
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = InstallRecord
        fields = [
            'id', 'skill', 'skill_name', 'user', 'username',
            'version', 'source', 'is_active', 'last_used', 'created_at'
        ]
        read_only_fields = ['user', 'created_at']


class ReviewRequestSerializer(serializers.ModelSerializer):
    """审核请求序列化器"""
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.username', 
                                          read_only=True, allow_null=True)
    
    class Meta:
        model = ReviewRequest
        fields = [
            'id', 'skill', 'skill_name', 'reviewer', 'reviewer_name',
            'notes', 'is_automated', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ReviewActionSerializer(serializers.Serializer):
    """审核操作序列化器"""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    reason = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class StatisticsSerializer(serializers.Serializer):
    """统计信息序列化器"""
    total_skills = serializers.IntegerField()
    approved_skills = serializers.IntegerField()
    pending_skills = serializers.IntegerField()
    total_installs = serializers.IntegerField()
    total_ratings = serializers.IntegerField()
    avg_rating = serializers.FloatField()

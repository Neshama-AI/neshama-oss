# -*- coding: utf-8 -*-
"""
Workshop 后台管理配置
Neshama Agent 项目
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Skill, SkillCategory, SkillVersion, CreatorProfile,
    Rating, InstallRecord, Favorite, ReviewRequest
)


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'sort_order', 'is_active', 'skill_count']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['sort_order', 'name']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'slug', 'description', 'icon')
        }),
        ('分类结构', {
            'fields': ('parent', 'sort_order')
        }),
        ('状态', {
            'fields': ('is_active',)
        }),
    )
    
    def skill_count(self, obj):
        count = obj.skills.filter(status='approved').count()
        return format_html('<b>{}</b>', count)
    skill_count.short_description = '技能数'


@admin.register(CreatorProfile)
class CreatorProfileAdmin(admin.ModelAdmin):
    list_display = ['username', 'level', 'title', 'skills_count', 'total_installs', 'avg_rating_display', 'verified', 'created_at']
    list_filter = ['level', 'verified']
    search_fields = ['user__username', 'title', 'bio']
    readonly_fields = ['skills_count', 'total_installs', 'total_ratings', 'avg_rating', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'avatar', 'bio')
        }),
        ('等级信息', {
            'fields': ('level', 'title')
        }),
        ('统计数据', {
            'fields': ('skills_count', 'total_installs', 'total_ratings', 'avg_rating'),
            'classes': ('collapse',)
        }),
        ('认证', {
            'fields': ('verified',)
        }),
    )
    
    def username(self, obj):
        return obj.user.username
    username.short_description = '用户名'
    
    def avg_rating_display(self, obj):
        if obj.avg_rating > 0:
            stars = '★' * int(obj.avg_rating)
            return format_html('{} ({:.1f})', stars, obj.avg_rating)
        return '-'
    avg_rating_display.short_description = '平均评分'


class SkillVersionInline(admin.TabularInline):
    model = SkillVersion
    extra = 0
    readonly_fields = ['install_count', 'created_at']
    fields = ['version', 'changelog', 'file_url', 'file_size', 'status', 'is_stable']


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'creator_link', 'category', 'status_badge', 'install_count', 'avg_rating_display', 'is_featured', 'created_at']
    list_filter = ['status', 'is_featured', 'is_premium', 'category', 'created_at']
    search_fields = ['name', 'slug', 'creator__user__username', 'tags']
    readonly_fields = ['install_count', 'rating_count', 'avg_rating', 'created_at', 'updated_at', 'published_at', 'reviewed_at']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SkillVersionInline]
    ordering = ['-created_at']
    list_per_page = 50
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'slug', 'creator', 'category', 'icon')
        }),
        ('描述', {
            'fields': ('short_description', 'full_description', 'tags')
        }),
        ('资源', {
            'fields': ('preview_images',)
        }),
        ('版本', {
            'fields': ('version', 'min_app_version')
        }),
        ('定价', {
            'fields': ('is_premium', 'price')
        }),
        ('状态', {
            'fields': ('status', 'reject_reason', 'is_featured')
        }),
        ('统计', {
            'fields': ('install_count', 'rating_count', 'avg_rating', 'reviewed_at', 'reviewed_by'),
            'classes': ('collapse',)
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_selected', 'reject_selected', 'mark_featured', 'unmark_featured']
    
    def creator_link(self, obj):
        url = reverse('admin:workshop_creatorprofile_change', args=[obj.creator.pk])
        return format_html('<a href="{}">{}</a>', url, obj.creator.user.username)
    creator_link.short_description = '创作者'
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'banned': '#343a40'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{};color:white;padding:3px 8px;border-radius:3px;font-size:11px">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = '状态'
    
    def avg_rating_display(self, obj):
        if obj.avg_rating > 0:
            stars = '★' * int(obj.avg_rating)
            return format_html('{} ({:.1f})', stars, obj.avg_rating)
        return '-'
    avg_rating_display.short_description = '评分'
    
    def approve_selected(self, request, queryset):
        count = queryset.update(status='approved')
        self.message_user(request, f'已通过 {count} 个技能')
    approve_selected.short_description = '批量通过选中技能'
    
    def reject_selected(self, request, queryset):
        count = queryset.update(status='rejected')
        self.message_user(request, f'已拒绝 {count} 个技能')
    reject_selected.short_description = '批量拒绝选中技能'
    
    def mark_featured(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, f'已标记 {count} 个技能为精选')
    mark_featured.short_description = '标记为精选'
    
    def unmark_featured(self, request, queryset):
        count = queryset.update(is_featured=False)
        self.message_user(request, f'已取消 {count} 个技能精选标记')
    unmark_featured.short_description = '取消精选标记'


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['skill_link', 'user', 'rating_stars', 'is_verified', 'helpful_count', 'created_at']
    list_filter = ['rating', 'is_verified', 'is_anonymous', 'created_at']
    search_fields = ['skill__name', 'user__username', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('skill', 'user', 'rating')
        }),
        ('评价', {
            'fields': ('comment', 'is_anonymous')
        }),
        ('状态', {
            'fields': ('is_verified', 'helpful_count')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def skill_link(self, obj):
        url = reverse('admin:workshop_skill_change', args=[obj.skill.pk])
        return format_html('<a href="{}">{}</a>', url, obj.skill.name)
    skill_link.short_description = '技能'
    
    def rating_stars(self, obj):
        return '★' * obj.rating
    rating_stars.short_description = '评分'


@admin.register(InstallRecord)
class InstallRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'skill_link', 'version', 'source', 'is_active', 'last_used', 'created_at']
    list_filter = ['is_active', 'source', 'created_at']
    search_fields = ['user__username', 'skill__name']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def skill_link(self, obj):
        url = reverse('admin:workshop_skill_change', args=[obj.skill.pk])
        return format_html('<a href="{}">{}</a>', url, obj.skill.name)
    skill_link.short_description = '技能'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'skill_link', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'skill__name']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def skill_link(self, obj):
        url = reverse('admin:workshop_skill_change', args=[obj.skill.pk])
        return format_html('<a href="{}">{}</a>', url, obj.skill.name)
    skill_link.short_description = '技能'


@admin.register(ReviewRequest)
class ReviewRequestAdmin(admin.ModelAdmin):
    list_display = ['skill_link', 'reviewer', 'is_automated', 'created_at', 'updated_at']
    list_filter = ['is_automated', 'created_at']
    search_fields = ['skill__name', 'reviewer__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def skill_link(self, obj):
        url = reverse('admin:workshop_skill_change', args=[obj.skill.pk])
        return format_html('<a href="{}">{}</a>', url, obj.skill.name)
    skill_link.short_description = '技能'

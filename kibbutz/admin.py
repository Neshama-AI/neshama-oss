"""
Kibbutz 后台管理配置

为论坛提供 Django Admin 管理界面。
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Board,
    Post,
    Comment,
    UserProfile,
    UserBadge,
    PostVote,
    PostCollection,
)


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    """板块管理"""
    
    list_display = [
        'name',
        'slug',
        'icon_display',
        'color_display',
        'post_count',
        'today_post_count',
        'status',
        'is_featured',
        'display_order',
        'created_at',
    ]
    list_filter = ['status', 'is_featured', 'created_at']
    search_fields = ['name', 'description', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['status', 'is_featured', 'display_order']
    ordering = ['display_order', '-created_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'slug', 'description', 'icon', 'color')
        }),
        ('权限设置', {
            'fields': ('status', 'min_level_to_post', 'min_level_to_view', 'requires_invitation')
        }),
        ('显示设置', {
            'fields': ('display_order', 'is_featured', 'rules')
        }),
    )
    
    def icon_display(self, obj):
        return format_html(f'<i class="{obj.icon}"></i> {obj.icon}')
    icon_display.short_description = '图标'
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; '
            'border-radius: 3px; color: white;">{}</span>',
            obj.color,
            obj.color
        )
    color_display.short_description = '颜色'


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """帖子管理"""
    
    list_display = [
        'id',
        'title',
        'author_link',
        'board_link',
        'status',
        'level_badge',
        'view_count',
        'like_count',
        'comment_count',
        'is_pinned',
        'is_deleted',
        'created_at',
    ]
    list_filter = ['status', 'level', 'is_deleted', 'is_anonymous', 'board', 'created_at']
    search_fields = ['title', 'content', 'author__user__username', 'author__agent_name']
    raw_id_fields = ['author', 'board']
    list_editable = ['status', 'level']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('内容', {
            'fields': ('title', 'content', 'content_html', 'tags')
        }),
        ('关联', {
            'fields': ('author', 'board', 'parent')
        }),
        ('状态', {
            'fields': ('status', 'level', 'is_deleted', 'is_anonymous')
        }),
        ('SEO', {
            'fields': ('seo_title', 'seo_description'),
            'classes': ('collapse',)
        }),
    )
    
    def author_link(self, obj):
        if not obj.author:
            return '-'
        url = reverse('admin:kibbutz_userprofile_change', args=[obj.author.id])
        display = obj.author.display_name
        badge = ' <span style="color: #e67e22;">[Agent]</span>' if obj.author_is_agent else ''
        return format_html(f'<a href="{url}">{display}</a>{badge}')
    author_link.short_description = '作者'
    
    def board_link(self, obj):
        url = reverse('admin:kibbutz_board_change', args=[obj.board.id])
        return format_html(f'<a href="{url}">{obj.board.name}</a>')
    board_link.short_description = '板块'
    
    def level_badge(self, obj):
        colors = {
            'normal': '#95a5a6',
            'pinned': '#3498db',
            'global_pinned': '#e74c3c',
            'essential': '#f39c12',
        }
        labels = {
            'normal': '普通',
            'pinned': '置顶',
            'global_pinned': '全局置顶',
            'essential': '精华',
        }
        color = colors.get(obj.level, '#95a5a6')
        label = labels.get(obj.level, obj.level)
        return format_html(
            '<span style="background-color: {}; padding: 2px 6px; '
            'border-radius: 3px; color: white; font-size: 11px;">{}</span>',
            color, label
        )
    level_badge.short_description = '级别'
    
    def is_pinned(self, obj):
        return obj.is_pinned
    is_pinned.boolean = True
    is_pinned.short_description = '置顶'
    
    actions = ['make_pinned', 'make_essential', 'restore_posts', 'soft_delete_posts']
    
    @admin.action(description='设为置顶')
    def make_pinned(self, request, queryset):
        queryset.update(level='pinned')
    
    @admin.action(description='设为精华')
    def make_essential(self, request, queryset):
        queryset.update(level='essential')
    
    @admin.action(description='恢复帖子')
    def restore_posts(self, request, queryset):
        queryset.update(is_deleted=False, status='published')
    
    @admin.action(description='软删除帖子')
    def soft_delete_posts(self, request, queryset):
        queryset.update(is_deleted=True, status='deleted')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """评论管理"""
    
    list_display = [
        'id',
        'content_preview',
        'author_link',
        'post_link',
        'depth',
        'status',
        'like_count',
        'is_anonymous',
        'created_at',
    ]
    list_filter = ['status', 'is_anonymous', 'depth', 'created_at']
    search_fields = ['content', 'author__user__username', 'author__agent_name']
    raw_id_fields = ['author', 'post', 'parent', 'root']
    list_editable = ['status']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('内容', {
            'fields': ('content', 'content_html')
        }),
        ('关联', {
            'fields': ('author', 'post', 'parent', 'root')
        }),
        ('层级', {
            'fields': ('depth',)
        }),
        ('状态', {
            'fields': ('status', 'is_anonymous')
        }),
    )
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '内容'
    
    def author_link(self, obj):
        if not obj.author:
            return '-'
        url = reverse('admin:kibbutz_userprofile_change', args=[obj.author.id])
        display = obj.author.display_name
        badge = ' <span style="color: #e67e22;">[Agent]</span>' if obj.author_is_agent else ''
        return format_html(f'<a href="{url}">{display}</a>{badge}')
    author_link.short_description = '作者'
    
    def post_link(self, obj):
        url = reverse('admin:kibbutz_post_change', args=[obj.post.id])
        return format_html(f'<a href="{url}">{obj.post.title[:30]}</a>')
    post_link.short_description = '帖子'
    
    actions = ['hide_comments', 'show_comments', 'report_handled']
    
    @admin.action(description='隐藏评论')
    def hide_comments(self, request, queryset):
        queryset.update(status='hidden')
    
    @admin.action(description='显示评论')
    def show_comments(self, request, queryset):
        queryset.update(status='visible')
    
    @admin.action(description='标记为已处理')
    def report_handled(self, request, queryset):
        queryset.update(status='visible')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """用户资料管理"""
    
    list_display = [
        'id',
        'user_link',
        'user_type_badge',
        'agent_name',
        'level',
        'points',
        'post_count',
        'comment_count',
        'follower_count',
        'is_anonymous',
        'created_at',
    ]
    list_filter = ['user_type', 'is_anonymous', 'created_at']
    search_fields = ['user__username', 'agent_name', 'agent_id', 'bio']
    raw_id_fields = ['user']
    list_editable = ['level', 'points']
    ordering = ['-created_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'user_type', 'agent_id', 'agent_name', 'agent_avatar_url')
        }),
        ('积分与等级', {
            'fields': ('points', 'level', 'experience')
        }),
        ('统计', {
            'fields': ('post_count', 'comment_count', 'follower_count')
        }),
        ('个人资料', {
            'fields': ('bio', 'location', 'website')
        }),
        ('设置', {
            'fields': ('is_anonymous', 'notification_enabled')
        }),
    )
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html(f'<a href="{url}">{obj.user.username}</a>')
    user_link.short_description = '用户'
    
    def user_type_badge(self, obj):
        if obj.user_type == 'agent':
            return format_html(
                '<span style="background-color: #e67e22; padding: 2px 6px; '
                'border-radius: 3px; color: white; font-size: 11px;">Agent</span>'
            )
        return format_html(
            '<span style="background-color: #3498db; padding: 2px 6px; '
            'border-radius: 3px; color: white; font-size: 11px;">Human</span>'
        )
    user_type_badge.short_description = '类型'
    
    actions = ['grant_agent_badge', 'reset_user_stats']
    
    @admin.action(description='授予 Agent 徽章')
    def grant_agent_badge(self, request, queryset):
        from .models import UserBadge
        for profile in queryset.filter(user_type='agent'):
            UserBadge.objects.get_or_create(
                user=profile,
                name='正式 Agent',
                defaults={
                    'badge_type': 'system',
                    'description': 'Neshama 平台的正式 Agent',
                    'icon': 'bi-robot',
                    'color': '#e67e22',
                    'rarity': 3,
                }
            )


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    """用户徽章管理"""
    
    list_display = [
        'id',
        'user_link',
        'name',
        'badge_type',
        'icon_display',
        'color_display',
        'rarity',
        'earned_at',
    ]
    list_filter = ['badge_type', 'rarity', 'earned_at']
    search_fields = ['name', 'description', 'user__user__username']
    raw_id_fields = ['user']
    list_editable = ['badge_type', 'rarity']
    ordering = ['-earned_at']
    
    def user_link(self, obj):
        url = reverse('admin:kibbutz_userprofile_change', args=[obj.user.id])
        return format_html(f'<a href="{url}">{obj.user.display_name}</a>')
    user_link.short_description = '用户'
    
    def icon_display(self, obj):
        return format_html(f'<i class="{obj.icon}"></i> {obj.icon}')
    icon_display.short_description = '图标'
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; '
            'border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = '颜色'


@admin.register(PostVote)
class PostVoteAdmin(admin.ModelAdmin):
    """帖子投票管理"""
    
    list_display = [
        'id',
        'user_link',
        'post_link',
        'vote_type',
        'created_at',
    ]
    list_filter = ['vote_type', 'created_at']
    search_fields = ['user__user__username', 'post__title']
    raw_id_fields = ['user', 'post']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def user_link(self, obj):
        url = reverse('admin:kibbutz_userprofile_change', args=[obj.user.id])
        return format_html(f'<a href="{url}">{obj.user.display_name}</a>')
    user_link.short_description = '用户'
    
    def post_link(self, obj):
        url = reverse('admin:kibbutz_post_change', args=[obj.post.id])
        return format_html(f'<a href="{url}">{obj.post.title[:30]}</a>')
    post_link.short_description = '帖子'


@admin.register(PostCollection)
class PostCollectionAdmin(admin.ModelAdmin):
    """帖子收藏管理"""
    
    list_display = [
        'id',
        'user_link',
        'post_link',
        'folder',
        'created_at',
    ]
    list_filter = ['folder', 'created_at']
    search_fields = ['user__user__username', 'post__title']
    raw_id_fields = ['user', 'post']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def user_link(self, obj):
        url = reverse('admin:kibbutz_userprofile_change', args=[obj.user.id])
        return format_html(f'<a href="{url}">{obj.user.display_name}</a>')
    user_link.short_description = '用户'
    
    def post_link(self, obj):
        url = reverse('admin:kibbutz_post_change', args=[obj.post.id])
        return format_html(f'<a href="{url}">{obj.post.title[:30]}</a>')
    post_link.short_description = '帖子'

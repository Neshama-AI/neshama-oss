"""
清理垃圾内容命令

用于自动清理垃圾广告、重复内容、违规内容等。
可配置定时执行以保持社区清洁。
"""

from django.core.management.base import BaseCommand
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from kibbutz.models import (
    Post, 
    Comment, 
    Report, 
    UserProfile,
    SensitiveWord
)
from kibbutz.moderation import ModerationService, Moderation, UserBan


class Command(BaseCommand):
    help = '清理社区垃圾内容，包括广告、重复内容和过期数据'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            default='all',
            choices=['all', 'spam', 'reports', 'duplicates', 'expired', 'inactive'],
            help='清理模式'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要执行的操作，不实际删除'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='过期天数（用于判断内容是否过期）'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='单次处理数量上限'
        )
        parser.add_argument(
            '--auto-delete',
            action='store_true',
            help='自动删除高置信度的垃圾内容'
        )
    
    def handle(self, *args, **options):
        mode = options['mode']
        dry_run = options['dry_run']
        days = options['days']
        limit = options['limit']
        auto_delete = options['auto_delete']
        
        self.stdout.write(f'开始清理垃圾内容 (mode={mode}, dry_run={dry_run})')
        
        stats = {
            'posts_checked': 0,
            'comments_checked': 0,
            'spam_deleted': 0,
            'reports_resolved': 0,
            'duplicates_merged': 0,
            'users_warned': 0,
            'users_banned': 0,
        }
        
        # 清理垃圾广告
        if mode in ['all', 'spam']:
            post_stats = self.clean_spam_posts(dry_run, limit)
            comment_stats = self.clean_spam_comments(dry_run, limit)
            
            stats['posts_checked'] += post_stats['checked']
            stats['spam_deleted'] += post_stats['deleted']
            stats['comments_checked'] += comment_stats['checked']
            stats['spam_deleted'] += comment_stats['deleted']
        
        # 处理举报
        if mode in ['all', 'reports']:
            report_stats = self.process_reports(dry_run, limit)
            stats['reports_resolved'] = report_stats
        
        # 清理重复内容
        if mode in ['all', 'duplicates']:
            dup_stats = self.clean_duplicates(dry_run, limit)
            stats['duplicates_merged'] = dup_stats
        
        # 清理过期内容
        if mode in ['all', 'expired']:
            expired_stats = self.clean_expired_content(dry_run, days, limit)
            stats['spam_deleted'] += expired_stats
        
        # 清理不活跃用户内容
        if mode in ['all', 'inactive']:
            inactive_stats = self.clean_inactive_content(dry_run, days, limit)
            stats['spam_deleted'] += inactive_stats
        
        # 输出统计
        self.stdout.write('\n' + '='*50)
        self.stdout.write('清理完成统计:')
        self.stdout.write(f'  检查帖子: {stats["posts_checked"]}')
        self.stdout.write(f'  检查评论: {stats["comments_checked"]}')
        self.stdout.write(f'  删除垃圾: {stats["spam_deleted"]}')
        self.stdout.write(f'  处理举报: {stats["reports_resolved"]}')
        self.stdout.write(f'  合并重复: {stats["duplicates_merged"]}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] 以上为预览，实际未执行删除操作'))
        else:
            self.stdout.write(self.style.SUCCESS('\n垃圾内容清理完成'))
    
    def clean_spam_posts(self, dry_run, limit):
        """清理垃圾帖子"""
        self.stdout.write('\n[1] 检查垃圾帖子...')
        
        spam_patterns = self.get_spam_patterns()
        checked = 0
        deleted = 0
        
        # 获取近期帖子
        posts = Post.objects.filter(
            status='published',
            is_deleted=False,
            created_at__gte=timezone.now() - timedelta(days=7)
        )[:limit]
        
        for post in posts:
            checked += 1
            spam_score = self.calculate_spam_score(post, 'post')
            
            if spam_score > 0.8:  # 高置信度
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] 将删除垃圾帖子: #{post.id} "{post.title[:30]}" (spam_score={spam_score:.2f})')
                    deleted += 1
                elif auto_delete:
                    post.is_deleted = True
                    post.status = 'deleted'
                    post.save()
                    deleted += 1
                    self.stdout.write(f'  删除垃圾帖子: #{post.id}')
                    
            elif spam_score > 0.5:  # 中等置信度，标记
                self.stdout.write(f'  疑似垃圾帖子: #{post.id} (spam_score={spam_score:.2f})')
        
        return {'checked': checked, 'deleted': deleted}
    
    def clean_spam_comments(self, dry_run, limit):
        """清理垃圾评论"""
        self.stdout.write('\n[2] 检查垃圾评论...')
        
        checked = 0
        deleted = 0
        
        comments = Comment.objects.filter(
            status='visible',
            created_at__gte=timezone.now() - timedelta(days=7)
        )[:limit]
        
        for comment in comments:
            checked += 1
            spam_score = self.calculate_spam_score(comment, 'comment')
            
            if spam_score > 0.8:
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] 将删除垃圾评论: #{comment.id}')
                    deleted += 1
                elif auto_delete:
                    comment.status = 'deleted'
                    comment.save()
                    deleted += 1
        
        return {'checked': checked, 'deleted': deleted}
    
    def get_spam_patterns(self):
        """获取垃圾内容特征"""
        patterns = {
            'urls': [],
            'keywords': [],
            'suspicious_patterns': [
                r'点击下方', r'扫码', r'微信', r'QQ群', r'加我',
                r'代理', r'兼职', r'日结', r'高薪', r'无需审核',
                r'直接领取', r'限时免费', r'全网最低'
            ]
        }
        
        # 从敏感词库获取
        ad_words = SensitiveWord.objects.filter(
            word_type='ad',
            is_active=True
        ).values_list('word', flat=True)
        
        patterns['keywords'].extend(ad_words)
        
        return patterns
    
    def calculate_spam_score(self, content_obj, content_type):
        """
        计算垃圾内容置信度
        
        Returns:
            float: 0.0-1.0 的分数，越高越可能是垃圾
        """
        content = content_obj.content if hasattr(content_obj, 'content') else ''
        title = content_obj.title if hasattr(content_obj, 'title') else ''
        
        full_text = f'{title} {content}'.lower()
        patterns = self.get_spam_patterns()
        
        score = 0.0
        factors = []
        
        # 1. 检查垃圾关键词
        keyword_matches = 0
        for keyword in patterns['keywords']:
            if keyword.lower() in full_text:
                keyword_matches += 1
        
        if keyword_matches > 0:
            score += min(keyword_matches * 0.15, 0.45)
            factors.append(f'关键词匹配: {keyword_matches}')
        
        # 2. 检查可疑模式
        suspicious_matches = 0
        for pattern in patterns['suspicious_patterns']:
            import re
            if re.search(pattern, full_text):
                suspicious_matches += 1
        
        if suspicious_matches > 0:
            score += min(suspicious_matches * 0.1, 0.3)
        
        # 3. 检查链接数量
        url_count = len(re.findall(r'https?://[^\s]+', full_text))
        if url_count > 3:
            score += 0.2
        elif url_count > 1:
            score += 0.1
        
        # 4. 检查内容长度（过短可能是垃圾）
        if len(content.strip()) < 20:
            score += 0.15
        
        # 5. 检查特殊字符密度
        special_chars = len(re.findall(r'[^\w\s\u4e00-\u9fff]', content))
        special_ratio = special_chars / len(content) if len(content) > 0 else 0
        if special_ratio > 0.3:
            score += 0.1
        
        # 6. 检查是否来自被封禁用户
        if content_obj.author:
            banned = UserBan.objects.filter(
                user=content_obj.author,
                is_active=True,
                ban_type__in=['permanent', 'posting_ban']
            ).filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            ).exists()
            
            if banned:
                score += 0.5
        
        return min(score, 1.0)
    
    def process_reports(self, dry_run, limit):
        """处理举报"""
        self.stdout.write('\n[3] 处理过期举报...')
        
        # 获取待处理的重复举报
        threshold_date = timezone.now() - timedelta(days=7)
        
        resolved = 0
        
        # 自动关闭过期的待处理举报
        old_reports = Report.objects.filter(
            status='pending',
            created_at__lt=threshold_date
        )[:limit]
        
        for report in old_reports:
            if dry_run:
                self.stdout.write(f'  [DRY RUN] 将关闭过期举报: #{report.id}')
            else:
                report.status = 'dismissed'
                report.resolution = '自动关闭：超时未处理'
                report.save()
            resolved += 1
        
        self.stdout.write(f'  处理完成: {resolved} 个举报')
        return resolved
    
    def clean_duplicates(self, dry_run, limit):
        """清理重复内容"""
        self.stdout.write('\n[4] 检查重复内容...')
        
        merged = 0
        
        # 查找标题完全相同的近期帖子
        recent_date = timezone.now() - timedelta(days=1)
        
        duplicate_titles = Post.objects.filter(
            status='published',
            is_deleted=False,
            created_at__gte=recent_date
        ).values('title').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        for dup in duplicate_titles:
            posts = Post.objects.filter(
                title=dup['title'],
                status='published',
                is_deleted=False
            ).order_by('created_at')[1:]  # 保留第一个，删除后续
        
            for post in posts[:limit]:
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] 将删除重复帖子: #{post.id} "{post.title[:30]}"')
                else:
                    post.is_deleted = True
                    post.status = 'deleted'
                    post.save()
                merged += 1
        
        return merged
    
    def clean_expired_content(self, dry_run, days, limit):
        """清理过期内容"""
        self.stdout.write(f'\n[5] 检查 {days} 天前的过期内容...')
        
        threshold_date = timezone.now() - timedelta(days=days)
        deleted = 0
        
        # 删除无评论、无互动的旧草稿
        drafts = Post.objects.filter(
            status='draft',
            created_at__lt=threshold_date
        )[:limit]
        
        for draft in drafts:
            if dry_run:
                self.stdout.write(f'  [DRY RUN] 将删除过期草稿: #{draft.id}')
            else:
                draft.delete()
            deleted += 1
        
        return deleted
    
    def clean_inactive_content(self, dry_run, days, limit):
        """清理不活跃用户的内容"""
        self.stdout.write(f'\n[6] 检查不活跃用户的内容...')
        
        threshold_date = timezone.now() - timedelta(days=days)
        deleted = 0
        
        # 找出被封禁用户的内容
        banned_users = UserBan.objects.filter(
            is_active=True,
            ban_type__in=['permanent', 'posting_ban', 'temporary']
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).values_list('user_id', flat=True)
        
        # 删除被封禁用户的内容（可选，根据业务需求）
        # 这里默认不自动删除，只标记
        banned_posts = Post.objects.filter(
            author_id__in=banned_users,
            status='published',
            is_deleted=False
        ).order_by('-created_at')[:10]
        
        for post in banned_posts:
            self.stdout.write(f'  封禁用户帖子: #{post.id} (author: {post.author.display_name})')
        
        return deleted


# 导入需要的模块
import re

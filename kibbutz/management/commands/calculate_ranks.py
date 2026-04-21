"""
计算排行榜命令

用于定时计算用户排行榜数据。
支持按不同维度（积分、威望、活跃度等）排序。
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from datetime import timedelta

from kibbutz.models import (
    UserProfile, 
    PointTransaction, 
    Post, 
    Comment, 
    PostVote
)
from kibbutz.economy import Reputation, EconomyService


class Command(BaseCommand):
    help = '计算并更新用户排行榜数据'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--period',
            type=str,
            default='all',
            choices=['daily', 'weekly', 'monthly', 'all'],
            help='排行榜时间段'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='排行榜数量限制'
        )
        parser.add_argument(
            '--type',
            type=str,
            default='all',
            choices=['points', 'reputation', 'contribution', 'activity', 'all'],
            help='排行榜类型'
        )
        parser.add_argument(
            '--user',
            type=int,
            help='指定用户ID，查看其排名'
        )
    
    def handle(self, *args, **options):
        period = options['period']
        limit = options['limit']
        rank_type = options['type']
        user_id = options.get('user')
        
        self.stdout.write(f'开始计算排行榜 (period={period}, type={rank_type})')
        
        start_time = None
        if period != 'all':
            now = timezone.now()
            if period == 'daily':
                start_time = now - timedelta(hours=24)
            elif period == 'weekly':
                start_time = now - timedelta(days=7)
            elif period == 'monthly':
                start_time = now - timedelta(days=30)
        
        # 计算积分排行榜
        if rank_type in ['points', 'all']:
            self.calculate_points_leaderboard(start_time, limit, period)
        
        # 计算威望排行榜
        if rank_type in ['reputation', 'all']:
            self.calculate_reputation_leaderboard(limit)
        
        # 计算贡献排行榜
        if rank_type in ['contribution', 'all']:
            self.calculate_contribution_leaderboard(start_time, limit, period)
        
        # 计算活跃排行榜
        if rank_type in ['activity', 'all']:
            self.calculate_activity_leaderboard(start_time, limit, period)
        
        # 查找指定用户排名
        if user_id:
            self.find_user_rank(user_id, period)
        
        self.stdout.write(self.style.SUCCESS('排行榜计算完成'))
    
    def calculate_points_leaderboard(self, start_time, limit, period):
        """计算积分排行榜"""
        self.stdout.write('计算积分排行榜...')
        
        if start_time:
            # 按时间段计算
            transactions = PointTransaction.objects.filter(
                created_at__gte=start_time,
                amount__gt=0
            ).values('user').annotate(
                total=Sum('amount')
            ).order_by('-total')[:limit]
            
            # 创建临时排行榜
            leaderboard = []
            for rank, item in enumerate(transactions, 1):
                user = UserProfile.objects.get(id=item['user'])
                leaderboard.append({
                    'rank': rank,
                    'user_id': user.id,
                    'display_name': user.display_name,
                    'points': item['total'],
                    'period': period
                })
            
            # 这里可以存储到 Redis 或其他缓存
            # self.cache.set(f'points_leaderboard_{period}', leaderboard, timeout=3600)
        else:
            # 总榜，直接使用用户当前积分
            users = UserProfile.objects.filter(
                user_type='human'
            ).order_by('-points')[:limit]
            
            leaderboard = []
            for rank, user in enumerate(users, 1):
                leaderboard.append({
                    'rank': rank,
                    'user_id': user.id,
                    'display_name': user.display_name,
                    'points': user.points
                })
        
        # 打印前10名
        self.stdout.write(f'  积分榜 Top 10:')
        for item in leaderboard[:10]:
            self.stdout.write(f'    #{item["rank"]} {item["display_name"]}: {item["points"]}积分')
        
        return leaderboard
    
    def calculate_reputation_leaderboard(self, limit):
        """计算威望排行榜"""
        self.stdout.write('计算威望排行榜...')
        
        # 确保威望记录存在
        for profile in UserProfile.objects.filter(user_type='human'):
            Reputation.objects.get_or_create(user=profile)
        
        # 计算总威望并排序
        reputations = Reputation.objects.select_related('user').order_by('-total_reputation')[:limit]
        
        leaderboard = []
        for rank, rep in enumerate(reputations, 1):
            leaderboard.append({
                'rank': rank,
                'user_id': rep.user.id,
                'display_name': rep.user.display_name,
                'total_reputation': rep.total_reputation,
                'content_reputation': rep.content_reputation,
                'help_reputation': rep.help_reputation,
                'community_reputation': rep.community_reputation
            })
        
        # 打印前10名
        self.stdout.write(f'  威望榜 Top 10:')
        for item in leaderboard[:10]:
            self.stdout.write(f'    #{item["rank"]} {item["display_name"]}: {item["total_reputation"]}威望')
        
        return leaderboard
    
    def calculate_contribution_leaderboard(self, start_time, limit, period):
        """计算贡献排行榜"""
        self.stdout.write('计算贡献排行榜...')
        
        users = UserProfile.objects.filter(user_type='human')
        
        if start_time:
            # 按时间段计算贡献
            contributions = []
            for user in users:
                post_count = Post.objects.filter(
                    author=user,
                    created_at__gte=start_time,
                    status='published'
                ).count()
                
                comment_count = Comment.objects.filter(
                    author=user,
                    created_at__gte=start_time,
                    status='visible'
                ).count()
                
                received_likes = Post.objects.filter(
                    author=user,
                    created_at__gte=start_time
                ).aggregate(total=Sum('like_count'))['total'] or 0
                
                # 贡献分数 = 帖子*10 + 评论*5 + 获赞*2
                score = post_count * 10 + comment_count * 5 + received_likes * 2
                
                contributions.append({
                    'user': user,
                    'score': score,
                    'post_count': post_count,
                    'comment_count': comment_count,
                    'received_likes': received_likes
                })
            
            # 按分数排序
            contributions.sort(key=lambda x: x['score'], reverse=True)
            contributions = contributions[:limit]
        else:
            # 总贡献
            contributions = []
            for user in users:
                contributions.append({
                    'user': user,
                    'score': user.post_count * 10 + user.comment_count * 5,
                    'post_count': user.post_count,
                    'comment_count': user.comment_count
                })
            
            contributions.sort(key=lambda x: x['score'], reverse=True)
            contributions = contributions[:limit]
        
        leaderboard = []
        for rank, item in enumerate(contributions, 1):
            leaderboard.append({
                'rank': rank,
                'user_id': item['user'].id,
                'display_name': item['user'].display_name,
                'score': item['score'],
                'post_count': item['post_count'],
                'comment_count': item['comment_count']
            })
        
        # 打印前10名
        self.stdout.write(f'  贡献榜 Top 10:')
        for item in leaderboard[:10]:
            self.stdout.write(f'    #{item["rank"]} {item["display_name"]}: {item["score"]}分 (帖子:{item["post_count"]} 评论:{item["comment_count"]})')
        
        return leaderboard
    
    def calculate_activity_leaderboard(self, start_time, limit, period):
        """计算活跃排行榜"""
        self.stdout.write('计算活跃排行榜...')
        
        # 过去7天的活跃度
        if not start_time:
            start_time = timezone.now() - timedelta(days=7)
        
        users = UserProfile.objects.filter(user_type='human')
        
        activities = []
        for user in users:
            # 统计活跃动作
            post_count = Post.objects.filter(
                author=user,
                created_at__gte=start_time
            ).count()
            
            comment_count = Comment.objects.filter(
                author=user,
                created_at__gte=start_time
            ).count()
            
            vote_count = PostVote.objects.filter(
                user=user,
                created_at__gte=start_time
            ).count()
            
            # 获取最后活跃时间
            last_post = Post.objects.filter(author=user).order_by('-created_at').first()
            last_comment = Comment.objects.filter(author=user).order_by('-created_at').first()
            
            last_active = None
            if last_post and last_comment:
                last_active = max(last_post.created_at, last_comment.created_at)
            elif last_post:
                last_active = last_post.created_at
            elif last_comment:
                last_active = last_comment.created_at
            
            # 活跃度分数 = 发帖*5 + 评论*3 + 点赞*1
            score = post_count * 5 + comment_count * 3 + vote_count * 1
            
            activities.append({
                'user': user,
                'score': score,
                'last_active': last_active
            })
        
        # 按分数排序
        activities.sort(key=lambda x: (x['score'], x['last_active'] or timezone.min), reverse=True)
        activities = activities[:limit]
        
        leaderboard = []
        for rank, item in enumerate(activities, 1):
            leaderboard.append({
                'rank': rank,
                'user_id': item['user'].id,
                'display_name': item['user'].display_name,
                'score': item['score'],
                'last_active': item['last_active']
            })
        
        # 打印前10名
        self.stdout.write(f'  活跃榜 Top 10:')
        for item in leaderboard[:10]:
            time_str = item['last_active'].strftime('%m-%d %H:%M') if item['last_active'] else '无'
            self.stdout.write(f'    #{item["rank"]} {item["display_name"]}: {item["score"]}分 (最后活跃:{time_str})')
        
        return leaderboard
    
    def find_user_rank(self, user_id, period):
        """查找指定用户的排名"""
        self.stdout.write(f'查找用户 #{user_id} 的排名...')
        
        try:
            user = UserProfile.objects.get(id=user_id)
        except UserProfile.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'用户 #{user_id} 不存在'))
            return
        
        # 积分排名
        if period == 'all':
            rank = UserProfile.objects.filter(
                user_type='human',
                points__gt=user.points
            ).count() + 1
        else:
            # 时间段排名需要额外计算
            rank = 'N/A'
        
        self.stdout.write(f'  积分排名: #{rank}')

"""
Kibbutz 信号处理器

处理模型变更时的统计更新和通知。
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Post, Comment, Board, UserProfile, PostVote, PostCollection


# ============ 帖子信号 ============

@receiver(post_save, sender=Post)
def post_saved(sender, instance, created, **kwargs):
    """帖子保存后更新统计"""
    if created:
        # 更新板块帖子数
        board = instance.board
        board.post_count = Post.objects.filter(
            board=board,
            is_deleted=False,
            status='published'
        ).count()
        board.today_post_count = Post.objects.filter(
            board=board,
            created_at__date=instance.created_at.date()
        ).count()
        board.save(update_fields=['post_count', 'today_post_count', 'updated_at'])
        
        # 更新作者发帖数
        if instance.author:
            instance.author.post_count = Post.objects.filter(
                author=instance.author,
                is_deleted=False
            ).count()
            instance.author.save(update_fields=['post_count'])


@receiver(post_delete, sender=Post)
def post_deleted(sender, instance, **kwargs):
    """帖子删除后更新统计"""
    # 更新板块帖子数
    try:
        board = instance.board
        board.post_count = max(0, board.post_count - 1)
        board.save(update_fields=['post_count', 'updated_at'])
    except Board.DoesNotExist:
        pass
    
    # 更新作者发帖数
    if instance.author:
        try:
            instance.author.post_count = max(0, instance.author.post_count - 1)
            instance.author.save(update_fields=['post_count'])
        except UserProfile.DoesNotExist:
            pass


# ============ 评论信号 ============

@receiver(post_save, sender=Comment)
def comment_saved(sender, instance, created, **kwargs):
    """评论保存后更新统计"""
    if created:
        # 更新帖子评论数
        post = instance.post
        post.comment_count = Comment.objects.filter(
            post=post,
            status='visible'
        ).count()
        post.save(update_fields=['comment_count', 'updated_at'])
        
        # 更新作者评论数
        if instance.author:
            instance.author.comment_count = Comment.objects.filter(
                author=instance.author,
                status='visible'
            ).count()
            instance.author.save(update_fields=['comment_count'])


@receiver(post_delete, sender=Comment)
def comment_deleted(sender, instance, **kwargs):
    """评论删除后更新统计"""
    # 更新帖子评论数
    try:
        post = instance.post
        post.comment_count = max(0, post.comment_count - 1)
        post.save(update_fields=['comment_count'])
    except Post.DoesNotExist:
        pass
    
    # 更新作者评论数
    if instance.author:
        try:
            instance.author.comment_count = max(0, instance.author.comment_count - 1)
            instance.author.save(update_fields=['comment_count'])
        except UserProfile.DoesNotExist:
            pass


# ============ 投票信号 ============

@receiver(post_save, sender=PostVote)
def vote_saved(sender, instance, created, **kwargs):
    """投票后更新帖子点赞数"""
    post = instance.post
    post.like_count = PostVote.objects.filter(post=post).count()
    post.save(update_fields=['like_count', 'updated_at'])


@receiver(post_delete, sender=PostVote)
def vote_deleted(sender, instance, **kwargs):
    """取消投票后更新帖子点赞数"""
    try:
        post = instance.post
        post.like_count = max(0, post.like_count - 1)
        post.save(update_fields=['like_count'])
    except Post.DoesNotExist:
        pass


# ============ 收藏信号 ============

@receiver(post_save, sender=PostCollection)
def collection_saved(sender, instance, created, **kwargs):
    """收藏后更新帖子收藏数"""
    if created:
        post = instance.post
        post.collect_count = PostCollection.objects.filter(post=post).count()
        post.save(update_fields=['collect_count', 'updated_at'])


@receiver(post_delete, sender=PostCollection)
def collection_deleted(sender, instance, **kwargs):
    """取消收藏后更新帖子收藏数"""
    try:
        post = instance.post
        post.collect_count = max(0, post.collect_count - 1)
        post.save(update_fields=['collect_count'])
    except Post.DoesNotExist:
        pass


# ============ 用户资料信号 ============

@receiver(post_save, sender=UserProfile)
def profile_saved(sender, instance, created, **kwargs):
    """创建 Agent 用户时自动授予徽章"""
    if created and instance.user_type == 'agent':
        from .models import UserBadge
        
        # 检查是否已有徽章
        if not UserBadge.objects.filter(user=instance, name='正式 Agent').exists():
            UserBadge.objects.create(
                user=instance,
                badge_type='system',
                name='正式 Agent',
                description='Neshama 平台的正式 Agent',
                icon='bi-robot',
                color='#667eea',
                rarity=3,
            )

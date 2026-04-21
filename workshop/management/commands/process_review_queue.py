# -*- coding: utf-8 -*-
"""
Workshop 管理命令 - 处理审核队列
自动处理待审核技能
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User

from workshop.models import Skill, SkillStatus, ReviewRequest
from workshop.review_engine import (
    EnhancedAutomatedReviewer,
    CodeSecurityScanner,
    ContentComplianceChecker,
    ReviewQueueManager,
)


class Command(BaseCommand):
    help = '处理审核队列，自动审核技能'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='每次处理的技能数量 (默认: 20)',
        )
        parser.add_argument(
            '--auto-approve',
            action='store_true',
            help='自动批准通过审核的技能',
        )
        parser.add_argument(
            '--auto-reject',
            action='store_true',
            help='自动拒绝不符合条件的技能',
        )
        parser.add_argument(
            '--reviewer',
            type=str,
            help='指定审核员用户名',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示待处理队列，不执行审核',
        )
        parser.add_argument(
            '--show-queue',
            action='store_true',
            help='显示审核队列而不处理',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        auto_approve = options['auto_approve']
        auto_reject = options['auto_reject']
        reviewer_username = options.get('reviewer')
        dry_run = options['dry_run']
        show_queue = options['show_queue']

        self.stdout.write(self.style.NOTICE('=' * 60))
        self.stdout.write(self.style.NOTICE('Workshop 审核队列处理器'))
        self.stdout.write(self.style.NOTICE('=' * 60))

        # 获取审核员
        reviewer = None
        if reviewer_username:
            try:
                reviewer = User.objects.get(username=reviewer_username)
                self.stdout.write(f'审核员: {reviewer.username}')
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'审核员不存在: {reviewer_username}'))
                return

        # 初始化队列管理器
        queue_manager = ReviewQueueManager()

        if show_queue:
            self._show_queue(queue_manager, reviewer, limit)
            return

        # 获取待审核技能
        pending_skills = Skill.objects.filter(
            status=SkillStatus.PENDING
        ).select_related('creator', 'category').order_by('updated_at')[:limit]

        total = pending_skills.count()
        self.stdout.write(f'待处理: {total} 个技能')

        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ 队列已清空'))
            return

        approved = 0
        rejected = 0
        manual_review = 0

        for skill in pending_skills:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(f'处理: {skill.name}'))
            self.stdout.write(f'  创作者: {skill.creator.user.username}')
            self.stdout.write(f'  分类: {skill.category.name if skill.category else "未分类"}')
            self.stdout.write(f'  提交时间: {skill.updated_at}')

            # 执行自动化审核
            code_content = self._get_skill_code(skill)
            reviewer_engine = EnhancedAutomatedReviewer(skill, code_content)
            result = reviewer_engine.run_full_review()

            # 显示审核结果
            self._display_review_result(result, skill)

            # 决策处理
            decision = result['decision']
            review_request = ReviewRequest.objects.filter(skill=skill).first()

            if decision == 'approve':
                if auto_approve and not dry_run:
                    skill.approve(reviewer)
                    approved += 1
                    self.stdout.write(self.style.SUCCESS('  ✅ 自动通过'))
                else:
                    manual_review += 1
                    self.stdout.write(self.style.WARNING('  ⚠️  建议通过，待人工确认'))

            elif decision == 'reject':
                if auto_reject and not dry_run:
                    skill.reject(
                        reviewer or User.objects.filter(is_superuser=True).first(),
                        result.get('recommendation', '自动审核拒绝')
                    )
                    rejected += 1
                    self.stdout.write(self.style.ERROR('  ❌ 自动拒绝'))
                else:
                    manual_review += 1
                    self.stdout.write(self.style.ERROR('  ⚠️  建议拒绝，待人工确认'))

            else:  # manual
                manual_review += 1
                if review_request and not review_request.reviewer:
                    queue_manager.assign_reviewer(skill, reviewer)
                self.stdout.write(self.style.WARNING('  📋 需要人工审核'))

            # 安全检查详情
            if result.get('security', {}).get('total_issues', 0) > 0:
                self.stdout.write(self.style.WARNING(
                    f'  🔒 安全问题: {result["security"]["total_issues"]} 个 '
                    f'(最高风险: {result["security"].get("max_risk", "N/A")})'
                ))

            if dry_run:
                self.stdout.write(self.style.WARNING('  ⚠️  DRY RUN - 未执行实际操作'))

        # 汇总
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('=' * 60))
        self.stdout.write(f'处理完成! 共 {total} 个技能')
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY RUN 模式 - 未执行实际操作'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ 通过: {approved}'))
            self.stdout.write(self.style.ERROR(f'❌ 拒绝: {rejected}'))
            self.stdout.write(self.style.WARNING(f'📋 人工审核: {manual_review}'))
        self.stdout.write(self.style.NOTICE('=' * 60))

    def _show_queue(self, queue_manager, reviewer, limit):
        """显示审核队列"""
        queue = queue_manager.get_review_queue(reviewer, limit)

        if not queue:
            self.stdout.write(self.style.SUCCESS('✅ 队列为空'))
            return

        self.stdout.write(f'\n审核队列 (共 {len(queue)} 项):\n')

        for i, item in enumerate(queue, 1):
            skill = item['skill']
            priority = item['priority']
            score = item['priority_score']

            priority_color = {
                'urgent': self.style.ERROR,
                'high': self.style.WARNING,
                'normal': self.style.NOTICE,
                'low': self.style.SUCCESS,
            }.get(priority.value, self.style.NOTICE)

            self.stdout.write(f'{i}. {skill.name}')
            self.stdout.write(f'   创作者: {skill.creator.user.username}')
            self.stdout.write(f'   分类: {skill.category.name if skill.category else "未分类"}')
            self.stdout.write(f'   优先级: {priority_color(priority.label)} (分数: {score:.1f})')
            self.stdout.write(f'   等待时间: {(timezone.now() - skill.updated_at).days} 天')
            self.stdout.write('')

        # 审核员工作负载
        if reviewer:
            workload = queue_manager.get_reviewer_workload(reviewer)
            self.stdout.write(self.style.NOTICE('-' * 40))
            self.stdout.write(f'审核员: {reviewer.username}')
            self.stdout.write(f'待审数量: {workload["pending_count"]}')
            self.stdout.write(f'本周审核: {workload["recent_reviewed"]}')
            self.stdout.write(f'平均时长: {workload["avg_review_hours"]:.1f} 小时')
            self.stdout.write(f'容量充足: {"是" if workload["capacity_available"] else "否"}')

    def _get_skill_code(self, skill):
        """获取技能代码内容（模拟）"""
        # 实际应从 SkillVersion 获取文件内容
        return ''

    def _display_review_result(self, result, skill):
        """显示审核结果"""
        # 合规检查摘要
        compliance = result.get('compliance', {})
        summary = compliance.get('summary', {})

        self.stdout.write(f'  合规检查:')
        self.stdout.write(f'    - 通过: {summary.get("pass", 0)}')
        self.stdout.write(f'    - 警告: {summary.get("warn", 0)}')
        self.stdout.write(f'    - 失败: {summary.get("fail", 0)}')
        self.stdout.write(f'    - 人工: {summary.get("manual", 0)}')

        # 评分
        score = result.get('score')
        if score:
            self.stdout.write(f'  质量评分:')
            self.stdout.write(f'    - 总分: {score.get("total", 0)}')
            self.stdout.write(f'    - 代码质量: {score.get("code_quality", 0)}')
            self.stdout.write(f'    - 安全性: {score.get("security", 0)}')
            self.stdout.write(f'    - 完整性: {score.get("completeness", 0)}')
            self.stdout.write(f'    - 文档: {score.get("documentation", 0)}')
            self.stdout.write(f'    - 用户体验: {score.get("user_experience", 0)}')

        # 决策
        self.stdout.write(f'  审核决策: {result.get("decision", "unknown")}')
        self.stdout.write(f'  建议: {result.get("recommendation", "N/A")}')

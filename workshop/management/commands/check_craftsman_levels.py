# -*- coding: utf-8 -*-
"""
Workshop 管理命令 - 检查工匠等级
自动检查并更新工匠等级晋升
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from workshop.models import CreatorProfile, Skill, SkillStatus
from workshop.craftsman import CraftsmanLevelManager, LevelConfig, CraftsmanLevel


class Command(BaseCommand):
    help = '检查并更新工匠等级晋升'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示待晋升的工匠，不实际执行',
        )
        parser.add_argument(
            '--level',
            type=str,
            help='指定只检查特定等级 (novice/skilled/master)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制检查所有工匠，忽略缓存',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        level_filter = options.get('level')
        force = options['force']

        self.stdout.write(self.style.NOTICE('=' * 50))
        self.stdout.write(self.style.NOTICE('开始检查工匠等级...'))
        self.stdout.write(self.style.NOTICE('=' * 50))

        # 获取所有工匠
        queryset = CreatorProfile.objects.all()
        if level_filter:
            queryset = queryset.filter(level=level_filter)

        total = queryset.count()
        promoted = 0
        checked = 0

        for craftsman in queryset:
            manager = CraftsmanLevelManager(craftsman)
            
            # 检查晋升条件
            promotion_info = manager.check_auto_promotion()
            
            if promotion_info.get('can_promote'):
                checked += 1
                next_level = promotion_info.get('next_level')
                
                self.stdout.write('')
                self.stdout.write(self.style.WARNING(
                    f'⚠️  {craftsman.user.username} ({craftsman.get_level_display()}) '
                    f'符合晋升到 {LevelConfig.REQUIREMENTS[next_level].level_name} 的条件'
                ))
                
                # 显示详细信息
                self.stdout.write(f'   当前统计:')
                stats = promotion_info.get('stats', {})
                self.stdout.write(f'   - 技能数: {stats.get("skills_count", 0)}')
                self.stdout.write(f'   - 安装量: {stats.get("total_installs", 0)}')
                self.stdout.write(f'   - 平均评分: {stats.get("avg_rating", 0)}')
                self.stdout.write(f'   - 活跃天数: {stats.get("active_days", 0)}')
                
                self.stdout.write(f'   晋升要求:')
                req = promotion_info.get('requirement', {})
                self.stdout.write(f'   - 技能数 ≥ {req.get("min_skills", 0)} ✓')
                self.stdout.write(f'   - 安装量 ≥ {req.get("min_installs", 0)} ✓')
                self.stdout.write(f'   - 评分 ≥ {req.get("min_rating", 0)} ✓')
                self.stdout.write(f'   - 活跃天数 ≥ {req.get("min_active_days", 0)} ✓')
                
                if req.get('badges_required'):
                    self.stdout.write(f'   - 徽章: {", ".join(req.get("badges_required", []))} ✓')
                
                if not dry_run:
                    success = manager.promote(
                        level=next_level,
                        reason='系统自动检查晋升',
                        operator=None
                    )
                    if success:
                        promoted += 1
                        self.stdout.write(self.style.SUCCESS(
                            f'   ✅ 已晋升为 {LevelConfig.REQUIREMENTS[next_level].level_name}'
                        ))
                    else:
                        self.stdout.write(self.style.ERROR('   ❌ 晋升失败'))
            else:
                # 显示进度（可选）
                if force or checked < 5:
                    failed_checks = promotion_info.get('failed_checks', [])
                    if failed_checks:
                        self.stdout.write(f'\n  {craftsman.user.username}: 需要 {", ".join(failed_checks)}')

        # 检查降级条件
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('-' * 50))
        self.stdout.write(self.style.NOTICE('检查降级条件...'))
        self.stdout.write(self.style.NOTICE('-' * 50))
        
        demoted = 0
        for craftsman in queryset.exclude(level=CraftsmanLevel.NOVICE):
            manager = CraftsmanLevelManager(craftsman)
            demotion_triggers = manager.check_demotion_conditions()
            
            if demotion_triggers:
                self.stdout.write('')
                self.stdout.write(self.style.ERROR(
                    f'⚠️  {craftsman.user.username} 触发降级条件:'
                ))
                
                for trigger in demotion_triggers:
                    self.stdout.write(f'   - {trigger["reason"]}')
                    self.stdout.write(f'     建议降级至: {trigger["suggested_level"]}')
                
                if not dry_run:
                    suggested_level = demotion_triggers[0].get('suggested_level', 'novice')
                    success = manager.demote(
                        level=suggested_level,
                        reason=demotion_triggers[0]['reason'],
                        operator=None
                    )
                    if success:
                        demoted += 1
                        self.stdout.write(self.style.WARNING(
                            f'   ✅ 已降级至 {suggested_level}'
                        ))

        # 汇总
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('=' * 50))
        self.stdout.write(f'检查完成! 共检查 {total} 位工匠')
        if dry_run:
            self.stdout.write(self.style.WARNING(f'⚠️  DRY RUN 模式 - 未执行实际操作'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ 晋升: {promoted} 位'))
            self.stdout.write(self.style.ERROR(f'⚠️  降级: {demoted} 位'))
        self.stdout.write(self.style.NOTICE('=' * 50))

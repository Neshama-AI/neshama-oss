# -*- coding: utf-8 -*-
"""
Workshop 审核逻辑模块
Neshama Agent 项目 - 技能审查核心算法
"""

import re
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from django.conf import settings
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError


class ReviewResult(Enum):
    """审核结果枚举"""
    PASS = 'pass'
    FAIL = 'fail'
    WARN = 'warn'
    MANUAL = 'manual'


@dataclass
class ReviewItem:
    """审核项"""
    name: str
    status: ReviewResult
    message: str
    suggestion: str = ''
    weight: int = 1  # 权重


class AutomatedReviewer:
    """
    自动化审核器
    
    负责对技能进行初步自动化审核，包括：
    - 内容合规性检查
    - 技术规范检查
    - 完整性检查
    """

    # 敏感词列表（实际生产中应从数据库或配置加载）
    SENSITIVE_WORDS = [
        '色情', '赌博', '毒品', '暴力', '诈骗',
        '外挂', '黑客', '病毒', '木马', '钓鱼'
    ]

    # 必需字段
    REQUIRED_FIELDS = ['name', 'short_description', 'full_description', 'category']

    # 名称最小长度
    MIN_NAME_LENGTH = 2
    MAX_NAME_LENGTH = 50

    # 描述最小长度
    MIN_DESC_LENGTH = 20
    MAX_DESC_LENGTH = 5000

    def __init__(self, skill):
        """初始化审核器"""
        self.skill = skill
        self.review_items: List[ReviewItem] = []

    def run_all_checks(self) -> Tuple[ReviewResult, List[ReviewItem]]:
        """
        运行所有审核检查
        
        Returns:
            Tuple[ReviewResult, List[ReviewItem]]: 最终结果和审核项列表
        """
        self.review_items = []
        
        # 1. 完整性检查
        self.check_completeness()
        
        # 2. 名称合规性检查
        self.check_name_compliance()
        
        # 3. 描述内容检查
        self.check_description()
        
        # 4. 技术规范检查
        self.check_technical()
        
        # 5. 敏感词过滤
        self.check_sensitive_content()
        
        # 6. 链接和资源检查
        self.check_resources()
        
        # 7. 定价检查
        self.check_pricing()
        
        # 计算最终结果
        return self.calculate_result()

    def check_completeness(self) -> None:
        """检查信息完整性"""
        missing_fields = []
        
        for field in self.REQUIRED_FIELDS:
            value = getattr(self.skill, field, None)
            if not value:
                missing_fields.append(field)
        
        if missing_fields:
            self.review_items.append(ReviewItem(
                name='信息完整性',
                status=ReviewResult.FAIL,
                message=f'缺少必填字段: {", ".join(missing_fields)}',
                suggestion='请完善所有必填信息后重新提交',
                weight=10
            ))
        else:
            self.review_items.append(ReviewItem(
                name='信息完整性',
                status=ReviewResult.PASS,
                message='所有必填字段已填写'
            ))

    def check_name_compliance(self) -> None:
        """检查名称合规性"""
        name = self.skill.name
        
        # 长度检查
        if len(name) < self.MIN_NAME_LENGTH:
            self.review_items.append(ReviewItem(
                name='名称长度',
                status=ReviewResult.FAIL,
                message=f'名称过短，最少{self.MIN_NAME_LENGTH}个字符',
                suggestion='请使用更具描述性的名称'
            ))
            return
        elif len(name) > self.MAX_NAME_LENGTH:
            self.review_items.append(ReviewItem(
                name='名称长度',
                status=ReviewResult.FAIL,
                message=f'名称过长，最多{self.MAX_NAME_LENGTH}个字符',
                suggestion='请精简技能名称'
            ))
            return
        
        # 格式检查（不允许特殊字符开头或纯数字）
        if name[0].isdigit():
            self.review_items.append(ReviewItem(
                name='名称格式',
                status=ReviewResult.FAIL,
                message='名称不能以数字开头',
                suggestion='请修改名称开头'
            ))
        
        # 检查是否包含品牌词
        brand_keywords = ['微信', '支付宝', '抖音', '小红书', '淘宝', '京东']
        for brand in brand_keywords:
            if brand in name:
                self.review_items.append(ReviewItem(
                    name='品牌词检查',
                    status=ReviewResult.WARN,
                    message=f'名称中包含"{brand}"相关词汇，请确保有授权',
                    suggestion='如无授权请修改名称以避免侵权',
                    weight=2
                ))

        if not any(item.name == '名称长度' and item.status == ReviewResult.FAIL 
                   for item in self.review_items):
            self.review_items.append(ReviewItem(
                name='名称合规性',
                status=ReviewResult.PASS,
                message='名称格式合规'
            ))

    def check_description(self) -> None:
        """检查描述内容"""
        short_desc = self.skill.short_description
        full_desc = self.skill.full_description
        
        # 简短描述长度检查
        if len(short_desc) < 5:
            self.review_items.append(ReviewItem(
                name='简短描述',
                status=ReviewResult.FAIL,
                message='简短描述过短，应至少5个字符',
                suggestion='请提供更有吸引力的简短描述'
            ))
        elif len(short_desc) > 200:
            self.review_items.append(ReviewItem(
                name='简短描述',
                status=ReviewResult.WARN,
                message='简短描述过长，建议不超过200字符',
                suggestion='精简描述，突出核心功能'
            ))
        
        # 完整描述长度检查
        if len(full_desc) < self.MIN_DESC_LENGTH:
            self.review_items.append(ReviewItem(
                name='完整描述',
                status=ReviewResult.FAIL,
                message=f'完整描述过短，至少需要{self.MIN_DESC_LENGTH}个字符',
                suggestion='请详细描述技能功能和使用方法'
            ))
        elif len(full_desc) > self.MAX_DESC_LENGTH:
            self.review_items.append(ReviewItem(
                name='完整描述',
                status=ReviewResult.WARN,
                message=f'完整描述过长，建议不超过{self.MAX_DESC_LENGTH}字符',
                suggestion='精简描述内容'
            ))
        
        # 检查是否包含联系方式
        contact_patterns = [
            r'\d{11}',  # 手机号
            r'\w+@\w+\.\w+',  # 邮箱
            r'QQ\s*\d+',  # QQ号
            r'微信[：:\s]+\w+',  # 微信号
        ]
        
        for pattern in contact_patterns:
            if re.search(pattern, full_desc):
                self.review_items.append(ReviewItem(
                    name='联系方式',
                    status=ReviewResult.WARN,
                    message='描述中包含疑似联系方式的内容',
                    suggestion='建议移除联系方式，使用站内消息沟通',
                    weight=2
                ))
                break

    def check_technical(self) -> None:
        """检查技术规范"""
        # 检查slug格式
        slug = self.skill.slug
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', slug):
            self.review_items.append(ReviewItem(
                name='URL别名',
                status=ReviewResult.FAIL,
                message='URL别名格式不正确',
                suggestion='只允许小写字母、数字和连字符'
            ))
        
        # 检查标签
        tags = self.skill.tags or []
        if len(tags) == 0:
            self.review_items.append(ReviewItem(
                name='标签',
                status=ReviewResult.WARN,
                message='建议添加标签以提高可发现性',
                suggestion='添加3-5个相关标签',
                weight=1
            ))
        elif len(tags) > 10:
            self.review_items.append(ReviewItem(
                name='标签数量',
                status=ReviewResult.WARN,
                message='标签数量过多',
                suggestion='建议保留3-5个最相关的标签',
                weight=1
            ))
        
        # 检查版本号格式
        version = self.skill.version
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            self.review_items.append(ReviewItem(
                name='版本号',
                status=ReviewResult.FAIL,
                message='版本号格式不正确',
                suggestion='请使用语义化版本号，如 1.0.0'
            ))

    def check_sensitive_content(self) -> None:
        """检查敏感内容"""
        text_to_check = f"{self.skill.name} {self.skill.short_description} {self.skill.full_description}"
        
        found_words = []
        for word in self.SENSITIVE_WORDS:
            if word in text_to_check:
                found_words.append(word)
        
        if found_words:
            self.review_items.append(ReviewItem(
                name='敏感词检查',
                status=ReviewResult.MANUAL,
                message=f'检测到敏感词汇: {", ".join(found_words)}',
                suggestion='请确认内容合规性，将交由人工审核',
                weight=20
            ))
        else:
            self.review_items.append(ReviewItem(
                name='敏感词检查',
                status=ReviewResult.PASS,
                message='未检测到敏感词汇'
            ))

    def check_resources(self) -> None:
        """检查资源链接"""
        url_validator = URLValidator()
        
        # 检查图标
        if self.skill.icon:
            try:
                url_validator(self.skill.icon)
            except ValidationError:
                self.review_items.append(ReviewItem(
                    name='图标URL',
                    status=ReviewResult.FAIL,
                    message='图标URL格式不正确',
                    suggestion='请提供有效的图片链接'
                ))
        
        # 检查预览图
        preview_images = self.skill.preview_images or []
        invalid_images = []
        for idx, url in enumerate(preview_images):
            try:
                url_validator(url)
            except ValidationError:
                invalid_images.append(f'第{idx+1}张')
        
        if invalid_images:
            self.review_items.append(ReviewItem(
                name='预览图',
                status=ReviewResult.FAIL,
                message=f"{', '.join(invalid_images)}预览图URL无效",
                suggestion='请检查预览图链接'
            ))

    def check_pricing(self) -> None:
        """检查定价"""
        if self.skill.is_premium:
            if self.skill.price <= 0:
                self.review_items.append(ReviewItem(
                    name='定价',
                    status=ReviewResult.FAIL,
                    message='付费技能必须设置大于0的价格',
                    suggestion='请设置合理的定价'
                ))
        else:
            self.review_items.append(ReviewItem(
                name='定价',
                status=ReviewResult.PASS,
                message='免费技能无需定价'
            ))

    def calculate_result(self) -> Tuple[ReviewResult, List[ReviewItem]]:
        """计算最终审核结果"""
        fail_count = 0
        warn_count = 0
        manual_count = 0
        total_weight = 0
        
        for item in self.review_items:
            total_weight += item.weight
            if item.status == ReviewResult.FAIL:
                fail_count += item.weight
            elif item.status == ReviewResult.WARN:
                warn_count += item.weight
            elif item.status == ReviewResult.MANUAL:
                manual_count += item.weight
        
        # 判断逻辑
        if fail_count > 0:
            # 有失败的检查项，直接拒绝
            return ReviewResult.FAIL, self.review_items
        
        if manual_count > 0:
            # 需要人工介入
            return ReviewResult.MANUAL, self.review_items
        
        # 警告项超过50%权重，需要人工复核
        if warn_count > total_weight * 0.5:
            return ReviewResult.MANUAL, self.review_items
        
        if warn_count > 0:
            return ReviewResult.WARN, self.review_items
        
        return ReviewResult.PASS, self.review_items


class CraftsmanLevelChecker:
    """
    工匠等级评估器
    
    根据创作者的表现评估其工匠等级
    """

    # 等级要求配置
    LEVEL_REQUIREMENTS = {
        'novice': {
            'min_skills': 0,
            'min_installs': 0,
            'min_rating': 0,
            'min_ratings': 0
        },
        'skilled': {
            'min_skills': 3,
            'min_installs': 50,
            'min_rating': 4.0,
            'min_ratings': 5
        },
        'master': {
            'min_skills': 10,
            'min_installs': 500,
            'min_rating': 4.5,
            'min_ratings': 20
        },
        'legend': {
            'min_skills': 30,
            'min_installs': 5000,
            'min_rating': 4.8,
            'min_ratings': 100
        }
    }

    @classmethod
    def evaluate(cls, profile) -> Dict:
        """
        评估创作者等级
        
        Args:
            profile: CreatorProfile 实例
            
        Returns:
            Dict: 评估结果和建议
        """
        result = {
            'current_level': profile.level,
            'next_level': None,
            'qualifications': {},
            'gaps': {},
            'suggestions': []
        }
        
        # 检查升级条件
        if profile.level == 'novice':
            next_level = 'skilled'
        elif profile.level == 'skilled':
            next_level = 'master'
        elif profile.level == 'master':
            next_level = 'legend'
        else:
            result['next_level'] = None
            return result
        
        result['next_level'] = next_level
        requirements = cls.LEVEL_REQUIREMENTS[next_level]
        
        # 评估各项指标
        metrics = {
            'skills': profile.skills_count,
            'installs': profile.total_installs,
            'rating': float(profile.avg_rating),
            'ratings': profile.total_ratings
        }
        
        for metric, value in metrics.items():
            min_value = requirements.get(f'min_{metric}')
            if min_value is not None:
                result['qualifications'][metric] = {
                    'current': value,
                    'required': min_value,
                    'qualified': value >= min_value
                }
                if value < min_value:
                    result['gaps'][metric] = min_value - value
                    result['suggestions'].append(
                        f'{metric}需达到{min_value}，当前{value}，还需{result["gaps"][metric]}'
                    )
        
        return result


class QualityScoreCalculator:
    """
    技能质量评分计算器
    
    综合多个维度计算技能的总体质量分数
    """

    # 权重配置
    WEIGHTS = {
        'completeness': 0.15,  # 信息完整度
        'popularity': 0.25,    # 受欢迎程度
        'rating': 0.30,        # 用户评分
        'engagement': 0.20,    # 活跃度
        'premium': 0.10        # 付费加分
    }

    @classmethod
    def calculate(cls, skill) -> Dict:
        """
        计算技能质量分数
        
        Args:
            skill: Skill 实例
            
        Returns:
            Dict: 详细评分结果
        """
        scores = {}
        
        # 1. 信息完整度评分
        scores['completeness'] = cls._score_completeness(skill)
        
        # 2. 受欢迎程度评分（基于安装量）
        scores['popularity'] = cls._score_popularity(skill)
        
        # 3. 用户评分
        scores['rating'] = cls._score_rating(skill)
        
        # 4. 活跃度评分
        scores['engagement'] = cls._score_engagement(skill)
        
        # 5. 付费技能加分
        scores['premium'] = 1.0 if skill.is_premium else 0.5
        
        # 计算加权总分
        total_score = sum(
            scores[key] * cls.WEIGHTS[key] 
            for key in scores.keys()
        )
        
        return {
            'total_score': round(total_score, 2),
            'breakdown': {k: round(v, 2) for k, v in scores.items()},
            'grade': cls._get_grade(total_score)
        }

    @classmethod
    def _score_completeness(cls, skill) -> float:
        """计算信息完整度分数"""
        score = 0.0
        factors = [
            (skill.short_description, 0.1),
            (skill.full_description, 0.2),
            (skill.icon, 0.1),
            (skill.preview_images, 0.15),
            (skill.tags, 0.1),
            (skill.category, 0.1),
            (skill.version, 0.1),
        ]
        
        for value, weight in factors:
            if value:
                score += weight
        
        return score * 10  # 转换为0-10分

    @classmethod
    def _score_popularity(cls, skill) -> float:
        """计算受欢迎程度分数"""
        installs = skill.install_count
        
        # 对数曲线，越往后增长越慢
        import math
        score = math.log(installs + 1, 10) * 2
        
        # 上限10分
        return min(score, 10)

    @classmethod
    def _score_rating(cls, skill) -> float:
        """计算评分分数"""
        if skill.rating_count == 0:
            return 5.0  # 无评分时给5分
        
        return float(skill.avg_rating) * 2  # 5分制转10分制

    @classmethod
    def _score_engagement(cls, skill) -> float:
        """计算活跃度分数"""
        # 考虑评分数量和安装量的比例
        if skill.install_count == 0:
            return 5.0
        
        ratio = skill.rating_count / skill.install_count
        
        # 评分率越高说明活跃度越高
        score = min(ratio * 100, 10)
        return score

    @classmethod
    def _get_grade(cls, score: float) -> str:
        """根据分数获取等级"""
        if score >= 9.0:
            return 'S'
        elif score >= 8.0:
            return 'A'
        elif score >= 7.0:
            return 'B'
        elif score >= 6.0:
            return 'C'
        elif score >= 5.0:
            return 'D'
        else:
            return 'F'

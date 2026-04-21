# -*- coding: utf-8 -*-
"""
Workshop 审核引擎增强模块
Neshama Agent 项目 - 技能审查核心算法（增强版）

主要增强：
- 自动化代码安全扫描
- 内容合规深度检查
- 质量评分多维度权重可配置
- 人工审核队列智能排序
"""
import re
import hashlib
import json
import ast
import subprocess
import tempfile
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import Counter

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q, Count, F


class ReviewPriority(Enum):
    """审核优先级"""
    LOW = 1, '低'
    NORMAL = 2, '普通'
    HIGH = 3, '高'
    URGENT = 4, '紧急'


class RiskLevel(Enum):
    """风险等级"""
    SAFE = 'safe', '安全'
    LOW = 'low', '低风险'
    MEDIUM = 'medium', '中风险'
    HIGH = 'high', '高风险'
    CRITICAL = 'critical', '严重'


@dataclass
class SecurityCheckResult:
    """安全检查结果"""
    check_type: str
    risk_level: RiskLevel
    details: List[str] = field(default_factory=list)
    code_snippets: List[str] = field(default_factory=list)
    line_numbers: List[int] = field(default_factory=list)


@dataclass
class ReviewScore:
    """审核评分"""
    total: float
    code_quality: float
    security: float
    completeness: float
    documentation: float
    user_experience: float
    
    def as_dict(self) -> Dict:
        return {
            'total': self.total,
            'code_quality': self.code_quality,
            'security': self.security,
            'completeness': self.completeness,
            'documentation': self.documentation,
            'user_experience': self.user_experience,
        }


class CodeSecurityScanner:
    """
    代码安全扫描器
    
    检测：
    - SQL注入风险
    - 命令注入风险
    - XSS攻击风险
    - 敏感信息泄露
    - 恶意代码模式
    """
    
    # 危险函数模式
    DANGEROUS_PATTERNS = {
        'sql_injection': [
            r'execute\s*\(\s*["\'].*%.*["\']',
            r'execute\s*\(\s*["\'].*\+.*["\']',
            r'cursor\.execute\s*\(\s*[^\)]*\%[^\)]*\)',
        ],
        'command_injection': [
            r'os\.system\s*\(',
            r'subprocess\.call\s*\(',
            r'subprocess\.run\s*\([^)]*shell\s*=\s*True',
            r'eval\s*\(',
            r'exec\s*\(',
        ],
        'xss_risk': [
            r'response\.write\s*\([^)]*request\.GET',
            r'response\.write\s*\([^)]*request\.POST',
            r'render.*\s*\([^,]*request',
        ],
        'sensitive_leak': [
            r'print\s*\([^)]*password',
            r'print\s*\([^)]*token',
            r'print\s*\([^)]*api_key',
            r'logger\.\w+\s*\([^)]*(password|token|secret)',
        ],
        'malicious': [
            r'import\s+(os|subprocess|shutil).*#\s*hidden',
            r'__import__\s*\([\'"]os[\'"]',
            r'getattr\s*\([^)]*,\s*[\'"]__.*__[\'"]',
        ],
    }
    
    # 敏感关键词
    SENSITIVE_KEYWORDS = [
        'password', 'passwd', 'secret', 'token', 'api_key',
        'access_key', 'private_key', 'credit_card', 'ssn',
    ]
    
    def __init__(self, code_content: str = '', file_path: str = ''):
        """
        初始化扫描器
        
        Args:
            code_content: 代码内容
            file_path: 代码文件路径
        """
        self.code_content = code_content
        self.file_path = file_path
        self.results: List[SecurityCheckResult] = []
        self.lines = code_content.split('\n') if code_content else []
    
    def scan(self) -> List[SecurityCheckResult]:
        """执行完整扫描"""
        if not self.code_content and not self.file_path:
            return []
        
        # 如果提供了文件路径，读取文件
        if not self.code_content and self.file_path and os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.code_content = f.read()
                self.lines = self.code_content.split('\n')
        
        self._scan_for_dangerous_patterns()
        self._scan_for_sensitive_keywords()
        self._scan_for_obfuscation()
        self._scan_for_network_operations()
        
        return self.results
    
    def _scan_for_dangerous_patterns(self) -> None:
        """扫描危险代码模式"""
        for check_type, patterns in self.DANGEROUS_PATTERNS.items():
            findings = []
            snippets = []
            line_nums = []
            
            for pattern in patterns:
                for idx, line in enumerate(self.lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append(f"检测到{check_type}模式: {line.strip()}")
                        snippets.append(line.strip())
                        line_nums.append(idx)
            
            if findings:
                risk_level = RiskLevel.HIGH if check_type == 'malicious' else RiskLevel.MEDIUM
                self.results.append(SecurityCheckResult(
                    check_type=check_type,
                    risk_level=risk_level,
                    details=findings,
                    code_snippets=snippets,
                    line_numbers=line_nums
                ))
    
    def _scan_for_sensitive_keywords(self) -> None:
        """扫描敏感关键词"""
        findings = []
        snippets = []
        line_nums = []
        
        for idx, line in enumerate(self.lines, 1):
            for keyword in self.SENSITIVE_KEYWORDS:
                if keyword in line.lower() and 'print' in line.lower():
                    findings.append(f"疑似泄露敏感信息({keyword}): {line.strip()}")
                    snippets.append(line.strip())
                    line_nums.append(idx)
                    break
        
        if findings:
            self.results.append(SecurityCheckResult(
                check_type='sensitive_leak',
                risk_level=RiskLevel.LOW,
                details=findings,
                code_snippets=snippets,
                line_numbers=line_nums
            ))
    
    def _scan_for_obfuscation(self) -> None:
        """扫描代码混淆"""
        findings = []
        snippets = []
        line_nums = []
        
        # 检测过长的单行代码
        for idx, line in enumerate(self.lines, 1):
            if len(line) > 500 and ';' in line:
                findings.append(f"疑似混淆代码(过长的复合语句): 行{idx}")
                snippets.append(line[:100] + '...')
                line_nums.append(idx)
        
        # 检测不常见的编码方式
        for idx, line in enumerate(self.lines, 1):
            if '\\x' in line or '\\u' in line:
                findings.append(f"检测到转义编码: 行{idx}")
                snippets.append(line.strip())
                line_nums.append(idx)
        
        if findings:
            self.results.append(SecurityCheckResult(
                check_type='obfuscation',
                risk_level=RiskLevel.MEDIUM,
                details=findings,
                code_snippets=snippets,
                line_numbers=line_nums
            ))
    
    def _scan_for_network_operations(self) -> None:
        """扫描网络操作"""
        findings = []
        snippets = []
        line_nums = []
        
        network_patterns = [
            r'requests\.',
            r'urllib\.',
            r'httpx\.',
            r'aiohttp\.',
            r'socket\.',
        ]
        
        for idx, line in enumerate(self.lines, 1):
            for pattern in network_patterns:
                if re.search(pattern, line):
                    findings.append(f"检测到网络操作: {line.strip()}")
                    snippets.append(line.strip())
                    line_nums.append(idx)
                    break
        
        if findings:
            self.results.append(SecurityCheckResult(
                check_type='network_ops',
                risk_level=RiskLevel.LOW,
                details=findings,
                code_snippets=snippets,
                line_numbers=line_nums
            ))
    
    def get_max_risk(self) -> RiskLevel:
        """获取最高风险等级"""
        if not self.results:
            return RiskLevel.SAFE
        
        risk_order = [RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        max_idx = 0
        for result in self.results:
            idx = risk_order.index(result.risk_level)
            if idx > max_idx:
                max_idx = idx
        
        return risk_order[max_idx]
    
    def get_summary(self) -> Dict:
        """获取扫描摘要"""
        return {
            'total_issues': len(self.results),
            'max_risk': self.get_max_risk().value,
            'issues_by_type': {
                result.check_type: {
                    'risk_level': result.risk_level.value,
                    'count': len(result.details),
                }
                for result in self.results
            }
        }


class ContentComplianceChecker:
    """
    内容合规检查器
    
    检测：
    - 敏感词过滤
    - 版权内容检测
    - 抄袭检测
    - 不当内容识别
    """
    
    # 敏感词库（实际应从数据库加载）
    SENSITIVE_WORDS = {
        'politics': ['暴力', '恐怖', '颠覆', '煽动'],
        'adult': ['色情', '裸体', '露骨'],
        'gambling': ['赌博', '博彩', '赌场'],
        'fraud': ['诈骗', '传销', '洗钱'],
        'illegal': ['毒品', '枪支', '炸药'],
    }
    
    # 品牌词库
    BRAND_KEYWORDS = [
        '微信', '支付宝', '抖音', '小红书', '淘宝', '京东', '拼多多',
        '腾讯', '阿里巴巴', '字节跳动', '百度', '美团', '滴滴',
    ]
    
    def __init__(self, skill):
        """初始化检查器"""
        self.skill = skill
        self.compliance_results: List[Dict] = []
    
    def check_all(self) -> Dict:
        """执行所有合规检查"""
        self._check_sensitive_content()
        self._check_brand_usage()
        self._check_contact_info()
        self._check_duplicate_content()
        self._check_description_quality()
        
        return {
            'is_compliant': all(r['status'] != 'fail' for r in self.compliance_results),
            'results': self.compliance_results,
            'summary': self._get_summary()
        }
    
    def _check_sensitive_content(self) -> None:
        """检查敏感内容"""
        text = f"{self.skill.name} {self.skill.short_description} {self.skill.full_description}"
        
        found_words = []
        for category, words in self.SENSITIVE_WORDS.items():
            for word in words:
                if word in text:
                    found_words.append(f"{category}:{word}")
        
        if found_words:
            self.compliance_results.append({
                'check_type': 'sensitive_content',
                'status': 'fail',
                'message': f'发现敏感词汇: {", ".join(found_words)}',
                'details': found_words
            })
        else:
            self.compliance_results.append({
                'check_type': 'sensitive_content',
                'status': 'pass',
                'message': '未检测到敏感词汇'
            })
    
    def _check_brand_usage(self) -> None:
        """检查品牌词使用"""
        text = f"{self.skill.name} {self.skill.short_description} {self.skill.full_description}"
        
        found_brands = [brand for brand in self.BRAND_KEYWORDS if brand in text]
        
        if found_brands:
            self.compliance_results.append({
                'check_type': 'brand_usage',
                'status': 'warn',
                'message': f'包含品牌词汇: {", ".join(found_brands)}',
                'details': found_brands,
                'suggestion': '请确保有授权使用这些品牌词汇'
            })
        else:
            self.compliance_results.append({
                'check_type': 'brand_usage',
                'status': 'pass',
                'message': '未检测到品牌词汇'
            })
    
    def _check_contact_info(self) -> None:
        """检查联系方式"""
        text = self.skill.full_description
        
        contact_patterns = {
            'phone': r'1[3-9]\d{9}',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'qq': r'QQ\s*[:：]?\s*\d{5,11}',
            'wechat': r'微信\s*[:：]?\s*\w+',
        }
        
        found_contacts = []
        for contact_type, pattern in contact_patterns.items():
            if re.search(pattern, text):
                found_contacts.append(contact_type)
        
        if found_contacts:
            self.compliance_results.append({
                'check_type': 'contact_info',
                'status': 'warn',
                'message': f'检测到联系方式: {", ".join(found_contacts)}',
                'details': found_contacts,
                'suggestion': '建议移除联系方式，使用站内消息'
            })
        else:
            self.compliance_results.append({
                'check_type': 'contact_info',
                'status': 'pass',
                'message': '未检测到联系方式'
            })
    
    def _check_duplicate_content(self) -> None:
        """检查重复内容（抄袭检测）"""
        # 简化版：使用文本哈希检测完全重复
        text_hash = hashlib.md5(
            self.skill.full_description.encode('utf-8')
        ).hexdigest()
        
        from .models import Skill, SkillStatus
        
        duplicate_count = Skill.objects.filter(
            status=SkillStatus.APPROVED
        ).annotate(
            desc_hash=Hash('full_description')
        ).filter(
            desc_hash=text_hash,
        ).count()
        
        if duplicate_count > 0:
            self.compliance_results.append({
                'check_type': 'duplicate_content',
                'status': 'manual',
                'message': f'检测到{duplicate_count}个相似描述',
                'details': f'文本哈希: {text_hash}',
                'suggestion': '需要人工审核确认是否抄袭'
            })
        else:
            self.compliance_results.append({
                'check_type': 'duplicate_content',
                'status': 'pass',
                'message': '未检测到重复内容'
            })
    
    def _check_description_quality(self) -> None:
        """检查描述质量"""
        issues = []
        
        # 检查描述长度
        if len(self.skill.full_description) < 50:
            issues.append('描述过短（少于50字）')
        elif len(self.skill.full_description) > 5000:
            issues.append('描述过长（超过5000字）')
        
        # 检查是否有使用说明
        if '使用' not in self.skill.full_description and '如何' not in self.skill.full_description:
            issues.append('缺少使用说明')
        
        # 检查是否有示例
        if '示例' not in self.skill.full_description and 'example' not in self.skill.full_description.lower():
            issues.append('缺少使用示例（建议添加）')
        
        if issues:
            status = 'fail' if len(self.skill.full_description) < 50 else 'warn'
            self.compliance_results.append({
                'check_type': 'description_quality',
                'status': status,
                'message': '描述质量有待提升',
                'details': issues
            })
        else:
            self.compliance_results.append({
                'check_type': 'description_quality',
                'status': 'pass',
                'message': '描述质量良好'
            })
    
    def _get_summary(self) -> Dict:
        """获取检查摘要"""
        status_count = Counter(r['status'] for r in self.compliance_results)
        
        return {
            'total_checks': len(self.compliance_results),
            'pass': status_count.get('pass', 0),
            'warn': status_count.get('warn', 0),
            'fail': status_count.get('fail', 0),
            'manual': status_count.get('manual', 0),
        }


class QualityScoreCalculator:
    """
    质量评分计算器（增强版）
    
    支持可配置的多维度评分权重
    """
    
    # 默认评分权重（可配置）
    DEFAULT_WEIGHTS = {
        'code_quality': 0.30,
        'security': 0.25,
        'completeness': 0.20,
        'documentation': 0.15,
        'user_experience': 0.10,
    }
    
    def __init__(self, skill, weights: Optional[Dict] = None):
        """
        初始化评分器
        
        Args:
            skill: 技能对象
            weights: 自定义评分权重（覆盖默认权重）
        """
        self.skill = skill
        self.weights = {**self.DEFAULT_WEIGHTS, **(weights or {})}
    
    def calculate(self, security_scan: Optional[List[SecurityCheckResult]] = None,
                  compliance_check: Optional[Dict] = None) -> ReviewScore:
        """
        计算综合评分
        
        Args:
            security_scan: 安全扫描结果
            compliance_check: 合规检查结果
        
        Returns:
            ReviewScore: 各维度评分及总分
        """
        code_quality = self._calculate_code_quality()
        security = self._calculate_security(security_scan)
        completeness = self._calculate_completeness()
        documentation = self._calculate_documentation()
        user_experience = self._calculate_user_experience()
        
        # 计算总分
        total = (
            code_quality * self.weights['code_quality'] +
            security * self.weights['security'] +
            completeness * self.weights['completeness'] +
            documentation * self.weights['documentation'] +
            user_experience * self.weights['user_experience']
        )
        
        return ReviewScore(
            total=round(total, 2),
            code_quality=round(code_quality, 2),
            security=round(security, 2),
            completeness=round(completeness, 2),
            documentation=round(documentation, 2),
            user_experience=round(user_experience, 2),
        )
    
    def _calculate_code_quality(self) -> float:
        """计算代码质量分"""
        score = 100.0
        
        # 检查版本号格式
        if not re.match(r'^\d+\.\d+\.\d+$', self.skill.version):
            score -= 10.0
        
        # 检查标签
        tags = self.skill.tags or []
        if not tags:
            score -= 5.0
        elif len(tags) > 10:
            score -= 5.0
        
        # 检查是否有预览图
        if not self.skill.preview_images:
            score -= 10.0
        
        # 检查是否有图标
        if not self.skill.icon:
            score -= 5.0
        
        # 检查是否选择了分类
        if not self.skill.category:
            score -= 15.0
        
        return max(0, min(100, score))
    
    def _calculate_security(self, security_scan: Optional[List[SecurityCheckResult]]) -> float:
        """计算安全性分"""
        if not security_scan:
            return 100.0
        
        scanner = CodeSecurityScanner('')
        scanner.results = security_scan
        max_risk = scanner.get_max_risk()
        summary = scanner.get_summary()
        
        # 根据风险等级扣分
        score = 100.0
        
        if max_risk == RiskLevel.CRITICAL:
            score -= 50.0
        elif max_risk == RiskLevel.HIGH:
            score -= 30.0
        elif max_risk == RiskLevel.MEDIUM:
            score -= 15.0
        elif max_risk == RiskLevel.LOW:
            score -= 5.0
        
        # 根据问题数量额外扣分
        score -= min(summary['total_issues'] * 2, 20)
        
        return max(0, min(100, score))
    
    def _calculate_completeness(self) -> float:
        """计算完整性分"""
        score = 0.0
        total_checks = 7
        
        # 必填项检查
        if self.skill.name and len(self.skill.name) >= 2:
            score += 1
        if self.skill.short_description and len(self.skill.short_description) >= 5:
            score += 1
        if self.skill.full_description and len(self.skill.full_description) >= 50:
            score += 1
        if self.skill.category:
            score += 1
        if self.skill.icon:
            score += 1
        if self.skill.preview_images:
            score += 1
        if self.skill.tags:
            score += 1
        
        return round((score / total_checks) * 100, 2)
    
    def _calculate_documentation(self) -> float:
        """计算文档质量分"""
        score = 100.0
        desc = self.skill.full_description
        
        # 长度检查
        if len(desc) < 100:
            score -= 30.0
        elif len(desc) < 300:
            score -= 15.0
        
        # 内容检查
        required_sections = ['功能', '使用', '说明', '示例']
        found_sections = sum(1 for section in required_sections if section in desc)
        score -= (4 - found_sections) * 10.0
        
        # 格式检查
        if '##' not in desc or '###' not in desc:
            score -= 20.0
        
        return max(0, min(100, score))
    
    def _calculate_user_experience(self) -> float:
        """计算用户体验分"""
        score = 100.0
        
        # 简短描述质量
        short_desc = self.skill.short_description
        if len(short_desc) < 10:
            score -= 20.0
        elif len(short_desc) > 150:
            score -= 10.0
        
        # 是否有清晰的描述
        if not any(keyword in self.skill.full_description for keyword in
                   ['功能', '特点', '优势', '适合']):
            score -= 20.0
        
        # 是否有场景说明
        if not any(keyword in self.skill.full_description for keyword in
                   ['场景', '应用', '适合', '推荐']):
            score -= 10.0
        
        return max(0, min(100, score))


class ReviewQueueManager:
    """
    审核队列管理器
    
    功能：
    - 智能优先级排序
    - 审核员负载均衡
    - 审核效率统计
    """
    
    PRIORITY_WEIGHTS = {
        ReviewPriority.URGENT: 100,
        ReviewPriority.HIGH: 75,
        ReviewPriority.NORMAL: 50,
        ReviewPriority.LOW: 25,
    }
    
    def __init__(self):
        self.cache_timeout = 3600  # 1小时
    
    def get_review_queue(self, reviewer: Optional[User] = None,
                        limit: int = 20) -> List:
        """
        获取审核队列（按优先级排序）
        
        Args:
            reviewer: 审核员（用于个性化排序）
            limit: 返回数量限制
        
        Returns:
            List: 待审核技能列表
        """
        from .models import ReviewRequest, Skill, SkillStatus, CreatorProfile
        
        # 获取待审核的技能
        pending_skills = Skill.objects.filter(
            status=SkillStatus.PENDING
        ).select_related('creator', 'creator__user', 'category').annotate(
            review_age=F('updated_at'),
            creator_level=F('creator__level'),
            rating=F('avg_rating')
        )
        
        # 计算每个技能的优先级分数
        queue = []
        for skill in pending_skills:
            priority_score = self._calculate_priority_score(skill, reviewer)
            queue.append({
                'skill': skill,
                'priority_score': priority_score,
                'priority': self._get_priority(priority_score),
            })
        
        # 按优先级排序
        queue.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return queue[:limit]
    
    def _calculate_priority_score(self, skill, reviewer: Optional[User]) -> float:
        """
        计算优先级分数
        
        考虑因素：
        - 等待时间
        - 创作者等级
        - 历史评分
        - 审核员专业匹配
        """
        score = 0.0
        
        # 1. 等待时间权重
        waiting_hours = (timezone.now() - skill.updated_at).total_seconds() / 3600
        if waiting_hours > 72:
            score += 40
        elif waiting_hours > 48:
            score += 30
        elif waiting_hours > 24:
            score += 20
        else:
            score += 10
        
        # 2. 创作者等级权重
        creator_level = skill.creator.level
        if creator_level == 'legend':
            score += 20
        elif creator_level == 'master':
            score += 15
        elif creator_level == 'skilled':
            score += 10
        else:
            score += 5
        
        # 3. 历史评分权重
        if skill.creator.avg_rating >= 4.5:
            score += 15
        elif skill.creator.avg_rating >= 4.0:
            score += 10
        else:
            score += 5
        
        # 4. 是否为首次提交
        if skill.creator.skills_count == 0:
            score += 10  # 优先审核新手
        
        # 5. 审核员专业匹配
        if reviewer and skill.category:
            is_expert = self._is_reviewer_expert(reviewer, skill.category)
            if is_expert:
                score += 10
        
        # 6. 是否付费技能
        if skill.is_premium:
            score += 15
        
        # 7. 是否有敏感标记
        has_sensitive = any(
            '敏感' in str(getattr(skill, 'review_items_cache', ''))
        )
        if has_sensitive:
            score += 25  # 优先处理敏感内容
        
        return score
    
    def _get_priority(self, score: float) -> ReviewPriority:
        """根据分数获取优先级"""
        if score >= 80:
            return ReviewPriority.URGENT
        elif score >= 60:
            return ReviewPriority.HIGH
        elif score >= 40:
            return ReviewPriority.NORMAL
        else:
            return ReviewPriority.LOW
    
    def _is_reviewer_expert(self, reviewer: User, category) -> bool:
        """判断审核员是否为该领域的专家"""
        # 简化实现：检查审核员在该分类下的审核数量
        from .models import ReviewRequest
        
        review_count = ReviewRequest.objects.filter(
            reviewer=reviewer,
            skill__category=category
        ).count()
        
        return review_count >= 10
    
    def assign_reviewer(self, skill, reviewer: User) -> bool:
        """
        分配审核员
        
        Args:
            skill: 待审核技能
            reviewer: 审核员
        
        Returns:
            bool: 是否分配成功
        """
        from .models import ReviewRequest
        
        review_request = ReviewRequest.objects.filter(skill=skill).first()
        if not review_request:
            review_request = ReviewRequest.objects.create(skill=skill)
        
        review_request.reviewer = reviewer
        review_request.save()
        
        return True
    
    def get_reviewer_workload(self, reviewer: User) -> Dict:
        """
        获取审核员工作负载
        
        Args:
            reviewer: 审核员
        
        Returns:
            Dict: 工作负载统计
        """
        from .models import ReviewRequest, SkillStatus
        
        pending = ReviewRequest.objects.filter(
            reviewer=reviewer,
            skill__status=SkillStatus.PENDING
        ).count()
        
        # 最近7天审核数量
        seven_days_ago = timezone.now() - timedelta(days=7)
        reviewed = ReviewRequest.objects.filter(
            reviewer=reviewer,
            skill__reviewed_at__gte=seven_days_ago
        ).count()
        
        # 平均审核时长
        recent_reviews = ReviewRequest.objects.filter(
            reviewer=reviewer,
            skill__reviewed_at__isnull=False
        ).order_by('-skill__reviewed_at')[:20]
        
        if recent_reviews:
            durations = []
            for r in recent_reviews:
                if r.skill.reviewed_at and r.created_at:
                    duration = (r.skill.reviewed_at - r.created_at).total_seconds() / 3600
                    durations.append(duration)
            avg_duration = sum(durations) / len(durations) if durations else 0
        else:
            avg_duration = 0
        
        return {
            'pending_count': pending,
            'recent_reviewed': reviewed,
            'avg_review_hours': round(avg_duration, 2),
            'capacity_available': pending < 20,
        }


class EnhancedAutomatedReviewer:
    """
    增强版自动化审核器
    
    整合所有检查模块，提供完整的自动化审核流程
    """
    
    def __init__(self, skill, code_content: str = ''):
        """
        初始化审核器
        
        Args:
            skill: 技能对象
            code_content: 代码内容（用于安全扫描）
        """
        self.skill = skill
        self.code_content = code_content
        self.security_results: List[SecurityCheckResult] = []
        self.compliance_results: Dict = {}
        self.score: Optional[ReviewScore] = None
    
    def run_full_review(self) -> Dict:
        """
        运行完整审核流程
        
        Returns:
            Dict: 审核结果
        """
        # 1. 代码安全扫描
        if self.code_content:
            scanner = CodeSecurityScanner(self.code_content)
            self.security_results = scanner.scan()
            security_summary = scanner.get_summary()
        else:
            security_summary = {'total_issues': 0, 'max_risk': 'safe'}
        
        # 2. 内容合规检查
        compliance_checker = ContentComplianceChecker(self.skill)
        self.compliance_results = compliance_checker.check_all()
        
        # 3. 质量评分
        score_calculator = QualityScoreCalculator(self.skill)
        self.score = score_calculator.calculate(self.security_results, self.compliance_results)
        
        # 4. 综合判断
        decision = self._make_decision(security_summary, self.compliance_results)
        
        return {
            'decision': decision,
            'security': security_summary,
            'compliance': self.compliance_results,
            'score': self.score.as_dict() if self.score else None,
            'recommendation': self._get_recommendation(decision),
        }
    
    def _make_decision(self, security_summary: Dict, compliance_results: Dict) -> str:
        """
        做出审核决策
        
        Returns:
            str: approve（通过）, reject（拒绝）, manual（人工审核）
        """
        # 严重安全问题直接拒绝
        if security_summary['max_risk'] == 'critical':
            return 'reject'
        
        # 合规检查失败直接拒绝
        if not compliance_results['is_compliant']:
            has_fail = any(r['status'] == 'fail' for r in compliance_results['results'])
            if has_fail:
                return 'reject'
        
        # 高风险或需要人工审核的标记
        if security_summary['max_risk'] in ['high', 'medium']:
            return 'manual'
        
        if any(r['status'] in ['manual', 'warn'] for r in compliance_results['results']):
            return 'manual'
        
        # 评分过低
        if self.score and self.score.total < 60:
            return 'manual'
        
        # 通过
        return 'approve'
    
    def _get_recommendation(self, decision: str) -> str:
        """获取审核建议"""
        recommendations = {
            'approve': '技能符合上架标准，建议通过审核',
            'reject': '技能存在严重问题，建议拒绝',
            'manual': '技能需要人工复核，请安排审核员详细审查',
        }
        return recommendations.get(deciation, '待审核')

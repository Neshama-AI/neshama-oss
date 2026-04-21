# -*- coding: utf-8 -*-
"""
Workshop 发现与推荐算法模块
Neshama Agent 项目 - 技能发现、对比、搜索与推荐系统
"""

from django.db.models import Q, Count, Avg, F, Func
from django.core.cache import cache
from django.contrib.auth.models import User
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import timedelta
import math
import hashlib


class FuzzyLength(Func):
    """模糊长度函数（用于MySQL）"""
    function = 'LENGTH'


@dataclass
class SearchResult:
    """搜索结果"""
    skill_id: int
    name: str
    slug: str
    short_description: str
    creator_name: str
    creator_level: str
    category: str
    category_slug: str
    avg_rating: float
    install_count: int
    is_premium: bool
    price: float
    icon: str
    relevance_score: float
    
    def to_dict(self) -> Dict:
        return {
            'id': self.skill_id,
            'name': self.name,
            'slug': self.slug,
            'short_description': self.short_description,
            'creator': {
                'name': self.creator_name,
                'level': self.creator_level,
            },
            'category': {
                'name': self.category,
                'slug': self.category_slug,
            },
            'rating': self.avg_rating,
            'installs': self.install_count,
            'is_premium': self.is_premium,
            'price': self.price,
            'icon': self.icon,
            'relevance_score': self.relevance_score,
        }


@dataclass
class CompareResult:
    """技能对比结果"""
    skills: List[Dict]
    comparison_matrix: Dict
    recommendations: List[str]


class SkillSearchEngine:
    """
    技能搜索引擎
    
    支持：
    - 全文搜索
    - 标签匹配
    - 分类筛选
    - 多条件组合
    - 智能排序
    """
    
    CACHE_PREFIX = 'skill_search'
    CACHE_TIMEOUT = 600  # 10分钟
    
    # 搜索权重配置
    WEIGHTS = {
        'name_match': 3.0,       # 名称匹配权重
        'tag_match': 2.0,        # 标签匹配权重
        'desc_match': 1.0,       # 描述匹配权重
        'rating_boost': 0.1,    # 评分加成系数
        'install_boost': 0.0001, # 安装量加成系数
    }
    
    def __init__(self):
        self.cache = cache
    
    def search(self, query: str, 
              category: Optional[str] = None,
              tags: Optional[List[str]] = None,
              min_rating: Optional[float] = None,
              min_installs: Optional[int] = None,
              is_premium: Optional[bool] = None,
              sort_by: str = 'relevance',
              page: int = 1,
              page_size: int = 20) -> Dict:
        """
        搜索技能
        
        Args:
            query: 搜索关键词
            category: 分类筛选
            tags: 标签筛选
            min_rating: 最低评分
            min_installs: 最低安装量
            is_premium: 是否付费
            sort_by: 排序方式 (relevance, rating, installs, latest)
            page: 页码
            page_size: 每页数量
        
        Returns:
            Dict: 搜索结果
        """
        from .models import Skill, SkillStatus, CreatorProfile
        
        # 构建查询
        queryset = Skill.objects.filter(
            status=SkillStatus.APPROVED
        ).select_related('creator', 'creator__user', 'category')
        
        # 分类筛选
        if category:
            queryset = queryset.filter(category__slug=category)
        
        # 标签筛选
        if tags:
            for tag in tags:
                queryset = queryset.filter(tags__contains=[tag])
        
        # 评分筛选
        if min_rating is not None:
            queryset = queryset.filter(avg_rating__gte=min_rating)
        
        # 安装量筛选
        if min_installs is not None:
            queryset = queryset.filter(install_count__gte=min_installs)
        
        # 付费筛选
        if is_premium is not None:
            queryset = queryset.filter(is_premium=is_premium)
        
        # 执行查询
        if query:
            results = self._calculate_relevance(queryset, query)
        else:
            results = self._default_sort(queryset, sort_by)
        
        # 分页
        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        page_results = results[start:end]
        
        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total / page_size),
            'results': [r.to_dict() for r in page_results],
        }
    
    def _calculate_relevance(self, queryset, query: str) -> List[SearchResult]:
        """计算搜索结果的相关性分数"""
        from .models import Skill
        
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        results = []
        
        for skill in queryset:
            relevance = 0.0
            
            # 名称匹配
            name_lower = skill.name.lower()
            if query_lower in name_lower:
                relevance += self.WEIGHTS['name_match'] * 2
            elif any(term in name_lower for term in query_terms):
                relevance += self.WEIGHTS['name_match']
            
            # 标签匹配
            tags = skill.tags or []
            tag_match_count = sum(1 for tag in tags if any(term in tag.lower() for term in query_terms))
            relevance += self.WEIGHTS['tag_match'] * tag_match_count
            
            # 描述匹配
            if query_lower in skill.short_description.lower():
                relevance += self.WEIGHTS['desc_match'] * 1.5
            elif any(term in skill.short_description.lower() for term in query_terms):
                relevance += self.WEIGHTS['desc_match']
            
            if query_lower in skill.full_description.lower():
                relevance += self.WEIGHTS['desc_match'] * 0.5
            
            # 评分加成
            relevance += float(skill.avg_rating) * self.WEIGHTS['rating_boost']
            
            # 安装量加成（对数处理）
            relevance += math.log1p(skill.install_count) * self.WEIGHTS['install_boost']
            
            results.append(SearchResult(
                skill_id=skill.id,
                name=skill.name,
                slug=skill.slug,
                short_description=skill.short_description,
                creator_name=skill.creator.user.username,
                creator_level=skill.creator.level,
                category=skill.category.name if skill.category else '',
                category_slug=skill.category.slug if skill.category else '',
                avg_rating=float(skill.avg_rating),
                install_count=skill.install_count,
                is_premium=skill.is_premium,
                price=float(skill.price),
                icon=skill.icon,
                relevance_score=relevance,
            ))
        
        # 按相关性排序
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results
    
    def _default_sort(self, queryset, sort_by: str) -> List[SearchResult]:
        """默认排序"""
        from .models import Skill
        
        if sort_by == 'rating':
            queryset = queryset.order_by('-avg_rating', '-install_count')
        elif sort_by == 'installs':
            queryset = queryset.order_by('-install_count', '-avg_rating')
        elif sort_by == 'latest':
            queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('-avg_rating', '-install_count')
        
        results = []
        for skill in queryset:
            results.append(SearchResult(
                skill_id=skill.id,
                name=skill.name,
                slug=skill.slug,
                short_description=skill.short_description,
                creator_name=skill.creator.user.username,
                creator_level=skill.creator.level,
                category=skill.category.name if skill.category else '',
                category_slug=skill.category.slug if skill.category else '',
                avg_rating=float(skill.avg_rating),
                install_count=skill.install_count,
                is_premium=skill.is_premium,
                price=float(skill.price),
                icon=skill.icon,
                relevance_score=0,
            ))
        
        return results


class RecommendationEngine:
    """
    智能推荐引擎
    
    推荐策略：
    - 协同过滤
    - 内容相似度
    - 热门推荐
    - 个性化推荐
    """
    
    CACHE_PREFIX = 'skill_recommend'
    CACHE_TIMEOUT = 1800  # 30分钟
    
    # 推荐类型
    RECOMMEND_TYPES = {
        'popular': '热门推荐',
        'similar': '相似推荐',
        'personalized': '个性化推荐',
        'trending': '趋势推荐',
        'new': '新品推荐',
        'curated': '编辑精选',
    }
    
    def __init__(self, user: Optional[User] = None):
        self.user = user
        self.cache = cache
    
    def get_recommendations(self, recommend_type: str = 'popular',
                          skill_id: Optional[int] = None,
                          category: Optional[str] = None,
                          limit: int = 10) -> List[Dict]:
        """
        获取推荐
        
        Args:
            recommend_type: 推荐类型
            skill_id: 参考技能ID（用于相似推荐）
            category: 分类筛选
            limit: 返回数量
        
        Returns:
            List[Dict]: 推荐列表
        """
        cache_key = f"{self.CACHE_PREFIX}_{recommend_type}_{skill_id}_{category}_{limit}"
        if self.user:
            cache_key += f"_{self.user.id}"
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        if recommend_type == 'popular':
            result = self._get_popular_recommendations(category, limit)
        elif recommend_type == 'similar':
            result = self._get_similar_recommendations(skill_id, limit)
        elif recommend_type == 'personalized':
            result = self._get_personalized_recommendations(limit)
        elif recommend_type == 'trending':
            result = self._get_trending_recommendations(category, limit)
        elif recommend_type == 'new':
            result = self._get_new_recommendations(category, limit)
        elif recommend_type == 'curated':
            result = self._get_curated_recommendations(limit)
        else:
            result = []
        
        self.cache.set(cache_key, result, self.CACHE_TIMEOUT)
        return result
    
    def _get_popular_recommendations(self, category: Optional[str], 
                                    limit: int) -> List[Dict]:
        """获取热门推荐"""
        from .models import Skill, SkillStatus
        
        queryset = Skill.objects.filter(
            status=SkillStatus.APPROVED
        ).select_related('creator', 'creator__user', 'category')
        
        if category:
            queryset = queryset.filter(category__slug=category)
        
        # 综合热门度评分
        queryset = queryset.annotate(
            hot_score=F('install_count') * 0.6 + F('rating_count') * 10 * 0.4
        ).order_by('-hot_score')[:limit]
        
        return [self._skill_to_dict(skill) for skill in queryset]
    
    def _get_similar_recommendations(self, skill_id: Optional[int],
                                   limit: int) -> List[Dict]:
        """获取相似推荐"""
        from .models import Skill, SkillStatus
        
        if not skill_id:
            return self._get_popular_recommendations(None, limit)
        
        try:
            reference_skill = Skill.objects.get(id=skill_id, status=SkillStatus.APPROVED)
        except Skill.DoesNotExist:
            return []
        
        # 基于分类和标签的相似度
        queryset = Skill.objects.filter(
            status=SkillStatus.APPROVED
        ).select_related('creator', 'creator__user', 'category').exclude(
            id=skill_id
        )
        
        # 相同分类
        if reference_skill.category:
            queryset = queryset.filter(category=reference_skill.category)
        
        # 计算相似度
        reference_tags = set(reference_skill.tags or [])
        results = []
        
        for skill in queryset:
            skill_tags = set(skill.tags or [])
            
            # Jaccard 相似度
            if reference_tags or skill_tags:
                intersection = len(reference_tags & skill_tags)
                union = len(reference_tags | skill_tags)
                tag_similarity = intersection / union if union > 0 else 0
            else:
                tag_similarity = 0
            
            # 综合评分
            similarity_score = (
                tag_similarity * 0.5 +
                float(skill.avg_rating) * 0.2 +
                math.log1p(skill.install_count) * 0.3 / 10
            )
            
            results.append({
                'skill': self._skill_to_dict(skill),
                'similarity_score': round(similarity_score, 3),
            })
        
        # 按相似度排序
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return [r['skill'] for r in results[:limit]]
    
    def _get_personalized_recommendations(self, limit: int) -> List[Dict]:
        """获取个性化推荐"""
        from .models import Skill, SkillStatus, InstallRecord
        
        if not self.user:
            return self._get_popular_recommendations(None, limit)
        
        # 获取用户已安装的技能
        installed_skills = InstallRecord.objects.filter(
            user=self.user,
            is_active=True
        ).values_list('skill_id', flat=True)
        
        # 获取用户偏好的分类和标签
        installed = Skill.objects.filter(id__in=installed_skills)
        
        category_scores: Dict[int, int] = {}
        tag_scores: Dict[str, int] = {}
        
        for skill in installed:
            if skill.category_id:
                category_scores[skill.category_id] = category_scores.get(skill.category_id, 0) + 1
            for tag in (skill.tags or []):
                tag_scores[tag] = tag_scores.get(tag, 0) + 1
        
        # 获取候选技能
        queryset = Skill.objects.filter(
            status=SkillStatus.APPROVED
        ).exclude(
            id__in=installed_skills
        ).select_related('creator', 'creator__user', 'category')
        
        # 计算个性化分数
        results = []
        for skill in queryset:
            score = 0.0
            
            # 分类匹配
            if skill.category_id:
                score += category_scores.get(skill.category_id, 0) * 2
            
            # 标签匹配
            for tag in (skill.tags or []):
                score += tag_scores.get(tag, 0) * 1.5
            
            # 基础质量
            score += float(skill.avg_rating) * 0.5
            
            results.append({
                'skill': self._skill_to_dict(skill),
                'personalized_score': round(score, 2),
            })
        
        results.sort(key=lambda x: x['personalized_score'], reverse=True)
        
        return [r['skill'] for r in results[:limit]]
    
    def _get_trending_recommendations(self, category: Optional[str],
                                     limit: int) -> List[Dict]:
        """获取趋势推荐（近期增长最快的）"""
        from .models import Skill, SkillStatus, InstallRecord
        from django.db.models.functions import TruncDate
        
        # 计算近7天新增安装量
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        queryset = Skill.objects.filter(
            status=SkillStatus.APPROVED
        ).select_related('creator', 'creator__user', 'category')
        
        if category:
            queryset = queryset.filter(category__slug=category)
        
        # 标注近期安装量
        recent_installs = InstallRecord.objects.filter(
            skill__in=queryset,
            created_at__gte=seven_days_ago
        ).values('skill').annotate(
            recent_count=Count('id')
        )
        
        recent_install_map = {item['skill']: item['recent_count'] for item in recent_installs}
        
        results = []
        for skill in queryset:
            recent_count = recent_install_map.get(skill.id, 0)
            
            # 趋势分数 = 近期安装量 / 总安装量 (增长率)
            growth_rate = recent_count / (skill.install_count + 1)
            
            results.append({
                'skill': self._skill_to_dict(skill),
                'recent_installs': recent_count,
                'growth_rate': round(growth_rate * 100, 1),
                'trending_score': round(growth_rate + math.log1p(skill.avg_rating), 3),
            })
        
        results.sort(key=lambda x: x['trending_score'], reverse=True)
        
        return [r['skill'] for r in results[:limit]]
    
    def _get_new_recommendations(self, category: Optional[str],
                                limit: int) -> List[Dict]:
        """获取新品推荐"""
        from .models import Skill, SkillStatus
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        queryset = Skill.objects.filter(
            status=SkillStatus.APPROVED,
            published_at__gte=thirty_days_ago
        ).select_related('creator', 'creator__user', 'category')
        
        if category:
            queryset = queryset.filter(category__slug=category)
        
        queryset = queryset.order_by('-published_at')[:limit]
        
        return [self._skill_to_dict(skill) for skill in queryset]
    
    def _get_curated_recommendations(self, limit: int) -> List[Dict]:
        """获取编辑精选"""
        from .models import Skill, SkillStatus
        
        queryset = Skill.objects.filter(
            status=SkillStatus.APPROVED,
            is_featured=True
        ).select_related('creator', 'creator__user', 'category')[:limit]
        
        return [self._skill_to_dict(skill) for skill in queryset]
    
    def _skill_to_dict(self, skill) -> Dict:
        """将技能对象转换为字典"""
        return {
            'id': skill.id,
            'name': skill.name,
            'slug': skill.slug,
            'short_description': skill.short_description,
            'icon': skill.icon,
            'rating': float(skill.avg_rating),
            'rating_count': skill.rating_count,
            'installs': skill.install_count,
            'is_premium': skill.is_premium,
            'price': float(skill.price),
            'category': {
                'name': skill.category.name if skill.category else '',
                'slug': skill.category.slug if skill.category else '',
            },
            'creator': {
                'name': skill.creator.user.username,
                'level': skill.creator.level,
                'avatar': skill.creator.avatar,
            },
        }


class SkillComparator:
    """
    技能对比分析器
    
    功能：
    - 多技能横向对比
    - 维度评分对比
    - 优劣势分析
    - 购买建议
    """
    
    # 对比维度
    COMPARE_DIMENSIONS = [
        'rating',
        'installs',
        'price',
        'documentation',
        'update_frequency',
        'support_quality',
    ]
    
    def __init__(self):
        self.cache = cache
    
    def compare(self, skill_ids: List[int]) -> CompareResult:
        """
        对比多个技能
        
        Args:
            skill_ids: 技能ID列表（2-5个）
        
        Returns:
            CompareResult: 对比结果
        """
        from .models import Skill, SkillStatus
        
        if len(skill_ids) < 2 or len(skill_ids) > 5:
            raise ValueError("对比技能数量需在2-5个之间")
        
        skills = Skill.objects.filter(
            id__in=skill_ids,
            status=SkillStatus.APPROVED
        ).select_related('creator', 'creator__user', 'category')
        
        if len(skills) < 2:
            raise ValueError("至少需要2个有效技能进行对比")
        
        # 构建对比数据
        skill_data = [self._get_skill_detail(s) for s in skills]
        
        # 计算对比矩阵
        comparison_matrix = self._build_comparison_matrix(skill_data)
        
        # 生成建议
        recommendations = self._generate_recommendations(skill_data)
        
        return CompareResult(
            skills=skill_data,
            comparison_matrix=comparison_matrix,
            recommendations=recommendations,
        )
    
    def _get_skill_detail(self, skill) -> Dict:
        """获取技能详细信息"""
        # 计算文档评分（基于描述长度）
        doc_score = min(len(skill.full_description) / 100, 10) if skill.full_description else 0
        
        # 估算更新频率
        update_score = 5  # 默认中等
        versions_count = skill.versions.count()
        if versions_count > 5:
            update_score = 10
        elif versions_count > 3:
            update_score = 7
        elif versions_count > 1:
            update_score = 5
        
        return {
            'id': skill.id,
            'name': skill.name,
            'slug': skill.slug,
            'icon': skill.icon,
            'short_description': skill.short_description,
            'rating': float(skill.avg_rating),
            'rating_count': skill.rating_count,
            'installs': skill.install_count,
            'is_premium': skill.is_premium,
            'price': float(skill.price),
            'version': skill.version,
            'updated_at': skill.updated_at.isoformat() if skill.updated_at else None,
            'creator': {
                'name': skill.creator.user.username,
                'level': skill.creator.level,
            },
            'dimensions': {
                'rating': float(skill.avg_rating),
                'installs': skill.install_count,
                'price': float(skill.price) if skill.is_premium else 0,
                'documentation': round(doc_score, 1),
                'update_frequency': update_score,
                'support_quality': float(skill.creator.avg_rating),
            },
        }
    
    def _build_comparison_matrix(self, skill_data: List[Dict]) -> Dict:
        """构建对比矩阵"""
        matrix = {}
        
        for dimension in self.COMPARE_DIMENSIONS:
            values = []
            
            for skill in skill_data:
                value = skill['dimensions'].get(dimension, 0)
                values.append({
                    'skill_id': skill['id'],
                    'skill_name': skill['name'],
                    'value': value,
                })
            
            # 排序找出最佳
            if dimension == 'price':
                values.sort(key=lambda x: x['value'])  # 价格越低越好
            else:
                values.sort(key=lambda x: x['value'], reverse=True)
            
            # 标记最佳
            if values:
                values[0]['is_best'] = True
                for i, v in enumerate(values[1:], 1):
                    v['is_best'] = False
            
            matrix[dimension] = values
        
        return matrix
    
    def _generate_recommendations(self, skill_data: List[Dict]) -> List[str]:
        """生成购买建议"""
        recommendations = []
        
        if len(skill_data) < 2:
            return recommendations
        
        # 评分最高
        best_rating = max(skill_data, key=lambda x: x['rating'])
        recommendations.append(
            f"如果您注重质量体验，推荐「{best_rating['name']}」（评分 {best_rating['rating']}）"
        )
        
        # 安装量最高
        best_installs = max(skill_data, key=lambda x: x['installs'])
        if best_installs['id'] != best_rating['id']:
            recommendations.append(
                f"如果您注重社区认可，推荐「{best_installs['name']}」（{best_installs['installs']}次安装）"
            )
        
        # 免费推荐
        free_skills = [s for s in skill_data if not s['is_premium']]
        if free_skills:
            best_free = max(free_skills, key=lambda x: x['rating'])
            recommendations.append(
                f"如果您预算有限，推荐免费选项「{best_free['name']}」"
            )
        
        # 综合推荐
        best_overall = max(skill_data, key=lambda x: (
            x['rating'] * 0.4 +
            min(x['installs'] / 100, 10) * 0.3 +
            x['dimensions']['documentation'] * 0.2 +
            x['dimensions']['update_frequency'] * 0.1
        ))
        recommendations.append(
            f"综合推荐：「{best_overall['name']}」，在多个维度表现均衡"
        )
        
        return recommendations


class SkillDependencyManager:
    """
    技能依赖管理器
    
    功能：
    - 依赖声明与解析
    - 兼容性检查
    - 版本约束处理
    """
    
    def __init__(self, skill):
        self.skill = skill
        self.dependencies = skill.dependencies or {}
    
    def add_dependency(self, dependency_skill_id: int,
                      version_constraint: str = '>=1.0.0') -> bool:
        """
        添加依赖
        
        Args:
            dependency_skill_id: 依赖的技能ID
            version_constraint: 版本约束（如 >=1.0.0）
        
        Returns:
            bool: 是否添加成功
        """
        from .models import Skill
        
        try:
            dep_skill = Skill.objects.get(id=dependency_skill_id)
        except Skill.DoesNotExist:
            return False
        
        self.dependencies[str(dependency_skill_id)] = {
            'skill_id': dependency_skill_id,
            'name': dep_skill.name,
            'version_constraint': version_constraint,
        }
        
        self.skill.dependencies = self.dependencies
        self.skill.save(update_fields=['dependencies'])
        return True
    
    def remove_dependency(self, dependency_skill_id: int) -> bool:
        """移除依赖"""
        if str(dependency_skill_id) in self.dependencies:
            del self.dependencies[str(dependency_skill_id)]
            self.skill.dependencies = self.dependencies
            self.skill.save(update_fields=['dependencies'])
            return True
        return False
    
    def check_dependencies(self) -> Dict:
        """
        检查依赖是否满足
        
        Returns:
            Dict: 检查结果
        """
        from .models import Skill, SkillStatus
        
        results = {
            'satisfied': [],
            'unsatisfied': [],
            'missing': [],
        }
        
        for dep_id, dep_info in self.dependencies.items():
            try:
                dep_skill = Skill.objects.get(
                    id=int(dep_id),
                    status=SkillStatus.APPROVED
                )
            except Skill.DoesNotExist:
                results['missing'].append({
                    'skill_id': int(dep_id),
                    'name': dep_info.get('name', '未知'),
                    'reason': '技能不存在或未通过审核',
                })
                continue
            
            # 检查版本约束
            constraint = dep_info.get('version_constraint', '>=1.0.0')
            if not self._check_version_constraint(dep_skill.version, constraint):
                results['unsatisfied'].append({
                    'skill_id': dep_skill.id,
                    'name': dep_skill.name,
                    'current_version': dep_skill.version,
                    'required_constraint': constraint,
                    'reason': '版本不满足约束',
                })
            else:
                results['satisfied'].append({
                    'skill_id': dep_skill.id,
                    'name': dep_skill.name,
                    'version': dep_skill.version,
                })
        
        return results
    
    def _check_version_constraint(self, version: str, constraint: str) -> bool:
        """
        检查版本是否满足约束
        
        支持格式：
        - >=1.0.0
        - <=2.0.0
        - 1.0.0 (精确版本)
        - ^1.0.0 (兼容版本)
        - ~1.0.0 (补丁版本)
        """
        import re
        
        version_parts = [int(x) for x in version.split('.')]
        
        # 解析约束
        match = re.match(r'^([<>=^~]+)?(\d+\.\d+\.\d+)$', constraint)
        if not match:
            return True  # 无法解析时默认通过
        
        operator = match.group(1) or '=='
        required_version = match.group(2)
        required_parts = [int(x) for x in required_version.split('.')]
        
        # 补齐长度
        version_parts += [0] * (3 - len(version_parts))
        required_parts += [0] * (3 - len(required_parts))
        
        if operator == '==':
            return version_parts == required_parts
        elif operator == '>=':
            return version_parts >= required_parts
        elif operator == '<=':
            return version_parts <= required_parts
        elif operator == '>':
            return version_parts > required_parts
        elif operator == '<':
            return version_parts < required_parts
        elif operator == '^':  # 兼容版本（主版本不变）
            return version_parts[0] == required_parts[0]
        elif operator == '~':  # 补丁版本（主次版本不变）
            return version_parts[0] == required_parts[0] and version_parts[1] == required_parts[1]
        
        return True
    
    def get_install_tree(self) -> Dict:
        """
        获取完整的依赖安装树
        
        Returns:
            Dict: 依赖树结构
        """
        from .models import Skill
        
        def build_tree(skill, visited: Set[int] = None):
            if visited is None:
                visited = set()
            
            if skill.id in visited:
                return {'id': skill.id, 'name': skill.name, 'circular': True}
            
            visited.add(skill.id)
            
            deps = []
            for dep_id, dep_info in (skill.dependencies or {}).items():
                try:
                    dep_skill = Skill.objects.get(id=int(dep_id))
                    deps.append(build_tree(dep_skill, visited.copy()))
                except Skill.DoesNotExist:
                    deps.append({
                        'id': int(dep_id),
                        'name': dep_info.get('name', '未知'),
                        'missing': True,
                    })
            
            return {
                'id': skill.id,
                'name': skill.name,
                'version': skill.version,
                'dependencies': deps,
            }
        
        return build_tree(self.skill)

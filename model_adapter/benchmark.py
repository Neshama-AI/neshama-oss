"""
Neshama Model Adapter Layer - Benchmark Framework
模型评测框架

功能：
- 基准测试设计
- 性能对比分析
- 成本效益分析
- 质量评估
"""

import asyncio
import time
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Awaitable
from enum import Enum
from datetime import datetime
import statistics
import logging

logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """评测类型"""
    LATENCY = "latency"           # 延迟测试
    THROUGHPUT = "throughput"      # 吞吐量测试
    ACCURACY = "accuracy"          # 准确性测试
    COST_EFFICIENCY = "cost_efficiency"  # 成本效益
    QUALITY = "quality"            # 质量评估


class TaskCategory(Enum):
    """任务类别"""
    COMPLETION = "completion"      # 文本补全
    CHAT = "chat"                  # 对话
    CODE = "code"                  # 代码生成
    REASONING = "reasoning"        # 逻辑推理
    SUMMARIZATION = "summarization"  # 摘要
    TRANSLATION = "translation"    # 翻译


@dataclass
class BenchmarkTask:
    """评测任务"""
    name: str
    category: TaskCategory
    prompt: str
    expected_output: Optional[str] = None
    reference_outputs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """单次评测结果"""
    task_name: str
    model: str
    provider: str
    
    # 时间指标
    start_time: datetime
    end_time: datetime
    latency_ms: float
    
    # Token指标
    input_tokens: int
    output_tokens: int
    total_tokens: int
    
    # 响应内容
    output: str
    raw_response: Any = None
    
    # 质量指标
    quality_score: Optional[float] = None
    similarity_score: Optional[float] = None
    
    # 成本
    cost: float = 0.0
    
    # 状态
    success: bool = True
    error: Optional[str] = None
    
    @property
    def tokens_per_second(self) -> float:
        """每秒输出token数"""
        if self.latency_ms <= 0:
            return 0
        return (self.output_tokens / self.latency_ms) * 1000


@dataclass
class ModelBenchmarkReport:
    """模型评测报告"""
    model: str
    provider: str
    
    # 基本统计
    total_tasks: int
    success_tasks: int
    failed_tasks: int
    
    # 延迟统计 (ms)
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    
    # Token统计
    total_input_tokens: int
    total_output_tokens: int
    avg_output_length: float
    
    # 质量统计
    avg_quality_score: Optional[float] = None
    avg_similarity_score: Optional[float] = None
    
    # 成本统计
    total_cost: float = 0.0
    cost_per_1k_output_tokens: float = 0.0
    cost_per_task: float = 0.0
    
    # 吞吐量
    avg_tokens_per_second: float = 0.0
    tasks_per_minute: float = 0.0
    
    # 详细结果
    task_results: List[BenchmarkResult] = field(default_factory=list)
    
    # 元数据
    benchmark_time: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BenchmarkRunner:
    """评测执行器"""
    
    def __init__(
        self,
        model_adapter: Any = None,
        model_manager: Any = None,
        pricing: Optional[Dict[str, Any]] = None
    ):
        self.model_adapter = model_adapter
        self.model_manager = model_manager
        self.pricing = pricing or {}
        
        self._results: Dict[str, List[BenchmarkResult]] = {}
        self._lock = asyncio.Lock()
    
    def set_pricing(
        self,
        model: str,
        input_price: float = 0,
        output_price: float = 0,
        currency: str = "CNY"
    ):
        """设置模型定价"""
        self.pricing[model] = {
            "input_price": input_price,
            "output_price": output_price,
            "currency": currency
        }
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """计算成本"""
        if model not in self.pricing:
            return 0
        
        p = self.pricing[model]
        return (input_tokens * p["input_price"] + 
                output_tokens * p["output_price"]) / 1000
    
    async def run_single_task(
        self,
        task: BenchmarkTask,
        model: str,
        provider: Any,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> BenchmarkResult:
        """运行单个任务"""
        start_time = datetime.now()
        
        try:
            # 调用模型
            response = await provider.call(
                messages=task.prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # 提取响应
            if hasattr(response, 'content'):
                output = response.content
                usage = response.usage or {}
                model_name = response.model
                provider_name = response.provider
                error = response.error
                success = not bool(error)
            else:
                output = str(response)
                usage = {}
                model_name = model
                provider_name = getattr(provider, 'provider_name', 'unknown')
                error = None
                success = True
            
            # 计算成本
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 
                                       len(output) // 4)  # 估算
            cost = self.calculate_cost(model, input_tokens, output_tokens)
            
            return BenchmarkResult(
                task_name=task.name,
                model=model_name,
                provider=provider_name,
                start_time=start_time,
                end_time=end_time,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                output=output,
                raw_response=response,
                cost=cost,
                success=success,
                error=error
            )
            
        except Exception as e:
            end_time = datetime.now()
            return BenchmarkResult(
                task_name=task.name,
                model=model,
                provider=getattr(provider, 'provider_name', 'unknown'),
                start_time=start_time,
                end_time=end_time,
                latency_ms=(end_time - start_time).total_seconds() * 1000,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                output="",
                cost=0,
                success=False,
                error=str(e)
            )
    
    async def run_benchmark(
        self,
        tasks: List[BenchmarkTask],
        model: str,
        provider: Any,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        concurrency: int = 1
    ) -> ModelBenchmarkReport:
        """运行基准测试"""
        results = []
        
        if concurrency > 1:
            # 并发执行
            semaphore = asyncio.Semaphore(concurrency)
            
            async def run_with_semaphore(task: BenchmarkTask):
                async with semaphore:
                    return await self.run_single_task(
                        task, model, provider, temperature, max_tokens
                    )
            
            results = await asyncio.gather(*[
                run_with_semaphore(task) for task in tasks
            ])
        else:
            # 顺序执行
            for task in tasks:
                result = await self.run_single_task(
                    task, model, provider, temperature, max_tokens
                )
                results.append(result)
        
        return self._generate_report(model, getattr(provider, 'provider_name', 'unknown'), results)
    
    def _generate_report(
        self,
        model: str,
        provider: str,
        results: List[BenchmarkResult]
    ) -> ModelBenchmarkReport:
        """生成评测报告"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        if not successful:
            return ModelBenchmarkReport(
                model=model,
                provider=provider,
                total_tasks=len(results),
                success_tasks=0,
                failed_tasks=len(results),
                avg_latency_ms=0,
                p50_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                total_input_tokens=0,
                total_output_tokens=0,
                avg_output_length=0,
                total_cost=0,
                cost_per_1k_output_tokens=0,
                cost_per_task=0,
                avg_tokens_per_second=0,
                tasks_per_minute=0,
                task_results=results
            )
        
        latencies = [r.latency_ms for r in successful]
        output_lengths = [r.output_tokens for r in successful]
        costs = [r.cost for r in successful]
        
        # 计算百分位数
        sorted_latencies = sorted(latencies)
        
        def percentile(data: List[float], p: float) -> float:
            if not data:
                return 0
            index = int(len(data) * p / 100)
            return data[min(index, len(data) - 1)]
        
        total_cost = sum(costs)
        total_output = sum(output_lengths)
        
        # 吞吐量计算
        if latencies:
            avg_latency = statistics.mean(latencies)
            tasks_per_minute = (60 / avg_latency * 1000) if avg_latency > 0 else 0
            avg_tps = sum(r.tokens_per_second for r in successful) / len(successful)
        else:
            tasks_per_minute = 0
            avg_tps = 0
        
        return ModelBenchmarkReport(
            model=model,
            provider=provider,
            total_tasks=len(results),
            success_tasks=len(successful),
            failed_tasks=len(failed),
            avg_latency_ms=statistics.mean(latencies),
            p50_latency_ms=percentile(sorted_latencies, 50),
            p95_latency_ms=percentile(sorted_latencies, 95),
            p99_latency_ms=percentile(sorted_latencies, 99),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            total_input_tokens=sum(r.input_tokens for r in successful),
            total_output_tokens=total_output,
            avg_output_length=statistics.mean(output_lengths),
            total_cost=total_cost,
            cost_per_1k_output_tokens=(total_cost / total_output * 1000) if total_output > 0 else 0,
            cost_per_task=statistics.mean(costs),
            avg_tokens_per_second=avg_tps,
            tasks_per_minute=tasks_per_minute,
            task_results=results
        )


class QualityEvaluator:
    """质量评估器"""
    
    def __init__(self):
        self._scorers: Dict[str, Callable[[str, str], float]] = {}
    
    def register_scorer(
        self,
        name: str,
        scorer: Callable[[str, str], float]
    ):
        """注册评分器"""
        self._scorers[name] = scorer
    
    def evaluate(
        self,
        output: str,
        reference: str,
        method: str = "exact_match"
    ) -> float:
        """评估输出质量"""
        if method == "exact_match":
            return 1.0 if output.strip() == reference.strip() else 0.0
        
        elif method == "contains":
            return 1.0 if reference.strip() in output.strip() else 0.0
        
        elif method == "length_ratio":
            if not reference:
                return 0
            ratio = len(output) / len(reference)
            return min(1.0, ratio)
        
        elif method in self._scorers:
            return self._scorers[method](output, reference)
        
        return 0.0
    
    def evaluate_similarity(
        self,
        output: str,
        references: List[str]
    ) -> Dict[str, float]:
        """评估与多个参考答案的相似度"""
        scores = {}
        for i, ref in enumerate(references):
            scores[f"ref_{i}"] = self.evaluate(output, ref, "contains")
        
        if scores:
            scores["best"] = max(scores.values())
            scores["average"] = sum(scores.values()) / len(scores)
        
        return scores


class BenchmarkSuite:
    """评测套件"""
    
    def __init__(self):
        self._tasks: List[BenchmarkTask] = []
        self._default_tasks: Dict[str, List[BenchmarkTask]] = {}
        self._init_default_tasks()
    
    def _init_default_tasks(self):
        """初始化默认任务"""
        # 文本补全任务
        self._default_tasks["completion"] = [
            BenchmarkTask(
                name="complete_sentence",
                category=TaskCategory.COMPLETION,
                prompt="春天的花开了，空气中弥漫着"
            ),
            BenchmarkTask(
                name="complete_paragraph",
                category=TaskCategory.COMPLETION,
                prompt="人工智能技术的发展经历了三个阶段：第一阶段是"
            ),
        ]
        
        # 对话任务
        self._default_tasks["chat"] = [
            BenchmarkTask(
                name="greeting",
                category=TaskCategory.CHAT,
                prompt="你好，请介绍一下你自己"
            ),
            BenchmarkTask(
                name="question_answer",
                category=TaskCategory.CHAT,
                prompt="请解释什么是机器学习"
            ),
        ]
        
        # 代码任务
        self._default_tasks["code"] = [
            BenchmarkTask(
                name="code_comment",
                category=TaskCategory.CODE,
                prompt="请为以下Python函数添加docstring：\n\ndef calculate_fibonacci(n):\n    if n <= 1:\n        return n\n    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)"
            ),
            BenchmarkTask(
                name="code_debug",
                category=TaskCategory.CODE,
                prompt="请找出以下代码的问题并修复：\n\nfor i in range(10)\n    print(i)"
            ),
        ]
        
        # 推理任务
        self._default_tasks["reasoning"] = [
            BenchmarkTask(
                name="math_basic",
                category=TaskCategory.REASONING,
                prompt="小明有5个苹果，小红给了他3个，小明吃掉了2个，小明现在还有多少个苹果？"
            ),
            BenchmarkTask(
                name="logic_puzzle",
                category=TaskCategory.REASONING,
                prompt="有三个盒子：一个只装苹果，一个只装橙子，一个装苹果和橙子。盒子标签都错了。请打开一个盒子，如何确定每个盒子的内容？"
            ),
        ]
        
        # 摘要任务
        self._default_tasks["summarization"] = [
            BenchmarkTask(
                name="summarize_article",
                category=TaskCategory.SUMMARIZATION,
                prompt="请为以下文章写一个简短的摘要：\n\n人工智能（AI）是计算机科学的一个分支，致力于开发能够执行通常需要人类智能的任务的系统。这包括视觉感知、语音识别、决策制定和语言翻译等。AI技术经历了多个发展阶段，从早期的符号AI到今天的深度学习。"
            ),
        ]
    
    def add_task(self, task: BenchmarkTask):
        """添加评测任务"""
        self._tasks.append(task)
    
    def get_tasks(
        self,
        category: Optional[TaskCategory] = None,
        name_prefix: Optional[str] = None
    ) -> List[BenchmarkTask]:
        """获取任务列表"""
        tasks = self._tasks
        
        if category:
            tasks = [t for t in tasks if t.category == category]
        
        if name_prefix:
            tasks = [t for t in tasks if t.name.startswith(name_prefix)]
        
        return tasks
    
    def get_default_tasks(self, category: str) -> List[BenchmarkTask]:
        """获取默认任务"""
        return self._default_tasks.get(category, [])
    
    def load_from_file(self, filepath: str):
        """从文件加载任务"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for item in data.get("tasks", []):
            task = BenchmarkTask(
                name=item["name"],
                category=TaskCategory[item["category"].upper()],
                prompt=item["prompt"],
                expected_output=item.get("expected_output"),
                reference_outputs=item.get("reference_outputs", [])
            )
            self.add_task(task)


class ComparisonReport:
    """对比报告"""
    
    def __init__(self):
        self._reports: Dict[str, ModelBenchmarkReport] = {}
    
    def add_report(self, report: ModelBenchmarkReport):
        """添加报告"""
        key = f"{report.provider}:{report.model}"
        self._reports[key] = report
    
    def get_best_by_latency(self, percentile: str = "avg") -> Optional[str]:
        """获取延迟最低的模型"""
        if not self._reports:
            return None
        
        latency_key = f"{percentile}_latency_ms"
        best_key = min(
            self._reports.keys(),
            key=lambda k: getattr(self._reports[k], latency_key, float('inf'))
        )
        return best_key
    
    def get_best_by_cost(self) -> Optional[str]:
        """获取成本最低的模型"""
        if not self._reports:
            return None
        
        best_key = min(
            self._reports.keys(),
            key=lambda k: self._reports[k].cost_per_task
        )
        return best_key
    
    def get_best_by_quality(self) -> Optional[str]:
        """获取质量最高的模型"""
        if not self._reports:
            return None
        
        valid_reports = [
            (k, r) for k, r in self._reports.items()
            if r.avg_quality_score is not None
        ]
        
        if not valid_reports:
            return None
        
        best_key = max(
            valid_reports,
            key=lambda x: x[1].avg_quality_score
        )[0]
        return best_key
    
    def get_cost_efficiency_score(self, report: ModelBenchmarkReport) -> float:
        """计算成本效益分数"""
        if report.avg_latency_ms <= 0 or report.cost_per_task <= 0:
            return 0
        
        # 延迟分数 (越低越好，归一化)
        latency_score = 1000 / report.avg_latency_ms
        
        # 成本分数 (越低越好)
        cost_score = 1 / report.cost_per_task
        
        # 综合分数
        return latency_score * cost_score * 1000
    
    def generate_comparison(self) -> Dict[str, Any]:
        """生成对比报告"""
        comparison = {
            "models": {},
            "rankings": {
                "by_latency": [],
                "by_cost": [],
                "by_efficiency": []
            }
        }
        
        # 添加各模型详情
        for key, report in self._reports.items():
            comparison["models"][key] = {
                "provider": report.provider,
                "avg_latency_ms": report.avg_latency_ms,
                "p95_latency_ms": report.p95_latency_ms,
                "cost_per_task": report.cost_per_task,
                "total_cost": report.total_cost,
                "success_rate": report.success_tasks / report.total_tasks if report.total_tasks > 0 else 0,
                "avg_tokens_per_second": report.avg_tokens_per_second,
                "cost_efficiency_score": self.get_cost_efficiency_score(report)
            }
        
        # 排名
        by_latency = sorted(
            comparison["models"].items(),
            key=lambda x: x[1]["avg_latency_ms"]
        )
        comparison["rankings"]["by_latency"] = [k for k, _ in by_latency]
        
        by_cost = sorted(
            comparison["models"].items(),
            key=lambda x: x[1]["cost_per_task"]
        )
        comparison["rankings"]["by_cost"] = [k for k, _ in by_cost]
        
        by_efficiency = sorted(
            comparison["models"].items(),
            key=lambda x: x[1]["cost_efficiency_score"],
            reverse=True
        )
        comparison["rankings"]["by_efficiency"] = [k for k, _ in by_efficiency]
        
        return comparison


# 标准评测套件
def create_standard_benchmark() -> BenchmarkSuite:
    """创建标准评测套件"""
    suite = BenchmarkSuite()
    return suite


# 便捷函数
async def quick_benchmark(
    model: str,
    provider: Any,
    tasks: Optional[List[BenchmarkTask]] = None,
    temperature: float = 0.7
) -> ModelBenchmarkReport:
    """快速评测"""
    if tasks is None:
        suite = create_standard_benchmark()
        tasks = suite.get_default_tasks("chat")
    
    runner = BenchmarkRunner()
    return await runner.run_benchmark(tasks, model, provider, temperature)

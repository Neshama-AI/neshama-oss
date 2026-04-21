"""
Workflow Scheduler
Schedules and manages workflow executions
"""

import logging
from typing import Callable, Dict, Optional
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class WorkflowScheduler:
    """Manages workflow scheduling"""
    
    def __init__(self, executor_callback: Callable):
        self._scheduler = AsyncIOScheduler()
        self._executor_callback = executor_callback
        self._workflow_jobs: Dict[str, dict] = {}
        
    def register_workflow(self, workflow_id: str, trigger_config: dict):
        """Register a workflow with the scheduler"""
        trigger_type = trigger_config.get("type")
        
        job_id = f"workflow_{workflow_id}"
        
        if trigger_type == "schedule":
            self._register_schedule_trigger(job_id, workflow_id, trigger_config)
            
        elif trigger_type == "event":
            # Event triggers are handled differently (via message queue, webhook, etc.)
            self._register_event_trigger(job_id, workflow_id, trigger_config)
            
        elif trigger_type == "webhook":
            # Webhook triggers are handled via HTTP endpoints
            self._register_webhook_trigger(job_id, workflow_id, trigger_config)
            
        logger.info(f"Registered workflow {workflow_id} with {trigger_type} trigger")
        
    def _register_schedule_trigger(self, job_id: str, workflow_id: str, config: dict):
        """Register a cron-based schedule trigger"""
        cron_expr = config.get("cron", "")
        timezone = config.get("timezone", "UTC")
        
        # Parse cron expression
        # Format: minute hour day month day_of_week
        cron_parts = cron_expr.split()
        
        if len(cron_parts) >= 5:
            trigger = CronTrigger(
                minute=cron_parts[0],
                hour=cron_parts[1],
                day=cron_parts[2],
                month=cron_parts[3],
                day_of_week=cron_parts[4],
                timezone=timezone
            )
        else:
            # Try as standard cron with defaults
            trigger = CronTrigger.from_crontab(cron_expr, timezone=timezone)
            
        job = self._scheduler.add_job(
            func=self._executor_callback,
            trigger=trigger,
            args=[workflow_id],
            id=job_id,
            replace_existing=True
        )
        
        self._workflow_jobs[workflow_id] = {
            "job_id": job_id,
            "type": "schedule",
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None
        }
        
    def _register_event_trigger(self, job_id: str, workflow_id: str, config: dict):
        """Register an event-based trigger"""
        # Event triggers need an external event system
        # This is a placeholder - actual implementation would connect to message queue
        self._workflow_jobs[workflow_id] = {
            "job_id": job_id,
            "type": "event",
            "event": config.get("event"),
            "source": config.get("source", "any")
        }
        
    def _register_webhook_trigger(self, job_id: str, workflow_id: str, config: dict):
        """Register a webhook trigger"""
        # Webhook triggers need HTTP endpoint setup
        # This is a placeholder - actual implementation would start HTTP server
        self._workflow_jobs[workflow_id] = {
            "job_id": job_id,
            "type": "webhook",
            "path": config.get("path"),
            "method": config.get("method", "POST")
        }
        
    def unregister_workflow(self, workflow_id: str):
        """Unregister a workflow from the scheduler"""
        if workflow_id in self._workflow_jobs:
            job_info = self._workflow_jobs[workflow_id]
            job_id = job_info["job_id"]
            
            try:
                self._scheduler.remove_job(job_id)
            except Exception:
                pass  # Job might not exist
                
            del self._workflow_jobs[workflow_id]
            logger.info(f"Unregistered workflow {workflow_id} from scheduler")
            
    def trigger_workflow(self, workflow_id: str, event_data: dict = None):
        """Manually trigger a workflow"""
        self._executor_callback(workflow_id, event_data)
        
    def get_next_run_time(self, workflow_id: str) -> Optional[str]:
        """Get next scheduled run time for a workflow"""
        if workflow_id in self._workflow_jobs:
            return self._workflow_jobs[workflow_id].get("next_run")
        return None
        
    def get_all_scheduled(self) -> Dict[str, dict]:
        """Get all scheduled workflows"""
        result = {}
        for workflow_id, job_info in self._workflow_jobs.items():
            result[workflow_id] = job_info.copy()
            
            # Update next run time from scheduler
            try:
                job = self._scheduler.get_job(job_info["job_id"])
                if job and job.next_run_time:
                    result[workflow_id]["next_run"] = job.next_run_time.isoformat()
            except Exception:
                pass
                
        return result
        
    def pause_workflow(self, workflow_id: str):
        """Pause a scheduled workflow"""
        if workflow_id in self._workflow_jobs:
            job_id = self._workflow_jobs[workflow_id]["job_id"]
            try:
                self._scheduler.pause_job(job_id)
                self._workflow_jobs[workflow_id]["paused"] = True
            except Exception as e:
                logger.error(f"Failed to pause workflow {workflow_id}: {e}")
                
    def resume_workflow(self, workflow_id: str):
        """Resume a paused workflow"""
        if workflow_id in self._workflow_jobs:
            job_id = self._workflow_jobs[workflow_id]["job_id"]
            try:
                self._scheduler.resume_job(job_id)
                self._workflow_jobs[workflow_id]["paused"] = False
            except Exception as e:
                logger.error(f"Failed to resume workflow {workflow_id}: {e}")
                
    def start(self):
        """Start the scheduler"""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Workflow scheduler started")
            
    def stop(self):
        """Stop the scheduler"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Workflow scheduler stopped")
            
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._scheduler.running


class CronParser:
    """Utility for parsing and validating cron expressions"""
    
    # Cron field ranges
    RANGES = {
        "minute": (0, 59),
        "hour": (0, 23),
        "day": (1, 31),
        "month": (1, 12),
        "day_of_week": (0, 6)  # 0 = Monday
    }
    
    @classmethod
    def parse(cls, cron_expr: str) -> dict:
        """Parse a cron expression into components"""
        parts = cron_expr.strip().split()
        
        if len(parts) != 5:
            raise ValueError(
                f"Invalid cron expression: expected 5 fields, got {len(parts)}"
            )
            
        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "day_of_week": parts[4]
        }
        
    @classmethod
    def validate(cls, cron_expr: str) -> bool:
        """Validate a cron expression"""
        try:
            parts = cls.parse(cron_expr)
            
            for field_name, field_value in parts.items():
                min_val, max_val = cls.RANGES[field_name]
                
                # Handle special characters
                if field_value in ("*", "?"):
                    continue
                    
                # Handle ranges (e.g., 1-5)
                if "-" in field_value:
                    start, end = field_value.split("-")
                    if not (min_val <= int(start) <= max_val and min_val <= int(end) <= max_val):
                        return False
                        
                # Handle lists (e.g., 1,3,5)
                elif "," in field_value:
                    for val in field_value.split(","):
                        if not (min_val <= int(val) <= max_val):
                            return False
                            
                # Handle steps (e.g., */5)
                elif "/" in field_value:
                    base, step = field_value.split("/")
                    if base != "*" and not (min_val <= int(base) <= max_val):
                        return False
                        
                # Handle single value
                else:
                    if not (min_val <= int(field_value) <= max_val):
                        return False
                        
            return True
            
        except (ValueError, IndexError):
            return False
            
    @classmethod
    def describe(cls, cron_expr: str) -> str:
        """Generate human-readable description of cron expression"""
        parts = cls.parse(cron_expr)
        
        descriptions = []
        
        # Minute
        minute = parts["minute"]
        if minute == "*":
            descriptions.append("every minute")
        elif "/" in minute:
            step = minute.split("/")[1]
            descriptions.append(f"every {step} minutes")
        else:
            descriptions.append(f"at minute {minute}")
            
        # Hour
        hour = parts["hour"]
        if hour == "*":
            descriptions.append("every hour")
        elif "/" in hour:
            step = hour.split("/")[1]
            descriptions.append(f"every {step} hours")
        else:
            descriptions.append(f"at hour {hour}")
            
        # Day
        day = parts["day"]
        if day != "*":
            descriptions.append(f"on day {day}")
            
        # Month
        month = parts["month"]
        if month != "*":
            month_names = ["", "January", "February", "March", "April", "May", "June",
                          "July", "August", "September", "October", "November", "December"]
            descriptions.append(f"in {month_names[int(month)]}")
            
        # Day of week
        dow = parts["day_of_week"]
        if dow != "*":
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            descriptions.append(f"on {day_names[int(dow)]}")
            
        return ", ".join(descriptions)

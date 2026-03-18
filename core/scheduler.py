"""
Scheduler for automated posting and background tasks.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from dotenv import load_dotenv

load_dotenv()

class SchedulerManager:
    """Manages scheduled tasks for reel posting and maintenance."""

    def __init__(self):
        self.scheduler = None
        self.jobs = {}

    def initialize(self):
        """Initialize the scheduler."""
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 3,
            'misfire_grace_time': 30
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )

        self.scheduler.start()

    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown()

    def schedule_reel_post(self, job_id: str, post_time: datetime,
                          callback: Callable, args: List = None, kwargs: Dict = None):
        """Schedule a reel post."""
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}

        trigger = DateTrigger(run_date=post_time)
        job = self.scheduler.add_job(
            callback,
            trigger=trigger,
            id=job_id,
            args=args,
            kwargs=kwargs,
            replace_existing=True
        )

        self.jobs[job_id] = job
        return job

    def schedule_daily_analytics(self, callback: Callable, hour: int = 9):
        """Schedule daily analytics collection."""
        trigger = CronTrigger(hour=hour, minute=0)
        job = self.scheduler.add_job(
            callback,
            trigger=trigger,
            id='daily_analytics',
            replace_existing=True
        )

        self.jobs['daily_analytics'] = job
        return job

    def schedule_content_generation(self, job_id: str, interval_hours: int,
                                  callback: Callable, args: List = None, kwargs: Dict = None):
        """Schedule periodic content generation."""
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}

        trigger = CronTrigger(hour=f'*/{interval_hours}')
        job = self.scheduler.add_job(
            callback,
            trigger=trigger,
            id=job_id,
            args=args,
            kwargs=kwargs,
            replace_existing=True
        )

        self.jobs[job_id] = job
        return job

    def cancel_job(self, job_id: str):
        """Cancel a scheduled job."""
        if job_id in self.jobs:
            self.scheduler.remove_job(job_id)
            del self.jobs[job_id]

    def get_scheduled_jobs(self) -> List[Dict]:
        """Get list of scheduled jobs."""
        jobs_info = []
        for job in self.scheduler.get_jobs():
            jobs_info.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger)
            })
        return jobs_info

    def pause_job(self, job_id: str):
        """Pause a scheduled job."""
        if job_id in self.jobs:
            self.scheduler.pause_job(job_id)

    def resume_job(self, job_id: str):
        """Resume a paused job."""
        if job_id in self.jobs:
            self.scheduler.resume_job(job_id)
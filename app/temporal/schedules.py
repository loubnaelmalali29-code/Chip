"""Temporal schedules for Chip.

Schedules define recurring workflows (e.g., weekly challenges).
"""

import os
from datetime import datetime, timedelta
from typing import Optional

try:
    from temporalio.client import Client as TemporalClient
    from temporalio.common import CronSchedule
    HAS_TEMPORAL = True
except ImportError:
    HAS_TEMPORAL = False
    TemporalClient = None
    CronSchedule = None

from app.temporal.workflows import WeeklyChallengeWorkflow


async def ensure_weekly_challenge_schedule(client: TemporalClient) -> None:
    """Ensure the weekly challenge schedule is active.
    
    This creates or updates a schedule that runs WeeklyChallengeWorkflow every week.
    
    Args:
        client: Temporal client instance
    """
    if not HAS_TEMPORAL:
        return
    
    try:
        schedule_id = "weekly-challenge-schedule"
        
        # Check if schedule already exists
        try:
            existing = await client.get_schedule(schedule_id)
            print(f"Weekly challenge schedule already exists: {schedule_id}")
            return
        except:
            # Schedule doesn't exist, create it
            pass
        
        # Create schedule: Run every Monday at 9 AM
        # Cron: "0 9 * * 1" = Monday at 9:00 AM
        schedule = await client.create_schedule(
            schedule_id,
            CronSchedule("0 9 * * 1"),  # Every Monday at 9 AM
            WeeklyChallengeWorkflow.run,
            args=[1],  # Start with week 1
        )
        
        print(f"Weekly challenge schedule created: {schedule_id}")
        
    except Exception as e:
        print(f"Error creating weekly challenge schedule: {e}")


async def ensure_schedules(client: TemporalClient) -> None:
    """Ensure all required schedules are active.
    
    Args:
        client: Temporal client instance
    """
    await ensure_weekly_challenge_schedule(client)





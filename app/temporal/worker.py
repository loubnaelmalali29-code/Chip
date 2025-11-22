"""Temporal worker for Chip.

The worker runs workflows and activities. This should run as a separate process
or in a background thread alongside the FastAPI server.
"""

import asyncio
import os
from typing import Optional

try:
    from temporalio.client import Client as TemporalClient
    from temporalio.worker import Worker
    HAS_TEMPORAL = True
except ImportError:
    HAS_TEMPORAL = False
    TemporalClient = None
    Worker = None

from app.temporal.workflows import WeeklyChallengeWorkflow, NotifyMatchesWorkflow
from app.temporal import activities


async def run_worker() -> None:
    """Run the Temporal worker.
    
    This function starts a worker that can execute workflows and activities.
    It should run in a background task or separate process.
    """
    if not HAS_TEMPORAL:
        print("Warning: temporalio package not installed. Temporal worker will not start.")
        return
    
    # Get Temporal configuration
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    
    try:
        # Connect to Temporal
        client = await TemporalClient.connect(
            target_host=temporal_host,
            namespace=temporal_namespace,
        )
        
        print(f"Temporal worker connecting to {temporal_host}/{temporal_namespace}")
        
        # Create worker
        worker = Worker(
            client,
            task_queue="chip-tasks",
            workflows=[WeeklyChallengeWorkflow, NotifyMatchesWorkflow],
            activities=[
                activities.get_or_create_weekly_challenge,
                activities.get_active_users,
                activities.send_challenge_notification,
                activities.get_matching_users,
                activities.get_relevant_opportunities,
                activities.get_active_challenges,
                activities.send_match_notification,
            ],
        )
        
        print("Temporal worker started. Waiting for workflows...")
        
        # Run worker (this blocks)
        await worker.run()
        
    except Exception as e:
        print(f"Error running Temporal worker: {e}")
        print("Note: Make sure Temporal server is running (temporal server start-dev)")


def start_worker_background() -> Optional[asyncio.Task]:
    """Start the Temporal worker in a background task.
    
    Returns:
        Background task, or None if Temporal is not available
    """
    if not HAS_TEMPORAL:
        return None
    
    try:
        # Try to get existing event loop, or create new one
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Create task in background
        task = loop.create_task(run_worker())
        return task
    except Exception as e:
        print(f"Error starting Temporal worker: {e}")
        import traceback
        traceback.print_exc()
        return None


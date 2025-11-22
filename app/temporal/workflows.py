"""Temporal workflows for Chip.

Workflows define the business logic and orchestration for Chip's automated features.
"""

from datetime import timedelta
from typing import Dict, Any, Optional

from temporalio import workflow

# Import activities (they will be registered with the worker)
from app.temporal import activities


@workflow.defn
class WeeklyChallengeWorkflow:
    """Workflow for managing weekly challenges in the Challenge Project.
    
    This workflow:
    1. Gets the current week's challenge
    2. Sends notifications to active users
    3. Tracks submissions
    4. Schedules next week's challenge
    """
    
    @workflow.run
    async def run(self, week_number: int, challenge_id: Optional[str] = None) -> Dict[str, Any]:
        """Run the weekly challenge workflow.
        
        Args:
            week_number: Week number in the 6-week program (1-6)
            challenge_id: Optional challenge ID if challenge already exists
            
        Returns:
            Workflow result with challenge details
        """
        # Get or create challenge for this week
        if not challenge_id:
            challenge_id = await workflow.execute_activity(
                activities.get_or_create_weekly_challenge,
                week_number,
                start_to_close_timeout=timedelta(seconds=30),
            )
        
        # Get active users who should receive notifications
        active_users = await workflow.execute_activity(
            activities.get_active_users,
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        # Send notifications to all active users
        notification_results = []
        for user in active_users:
            result = await workflow.execute_activity(
                activities.send_challenge_notification,
                {
                    "user_id": user["id"],
                    "user_phone": user["phone_number"],
                    "challenge_id": challenge_id,
                    "week_number": week_number,
                },
                start_to_close_timeout=timedelta(seconds=30),
            )
            notification_results.append(result)
        
        return {
            "week_number": week_number,
            "challenge_id": challenge_id,
            "users_notified": len(active_users),
            "notification_results": notification_results,
        }


@workflow.defn
class NotifyMatchesWorkflow:
    """Workflow for notifying users about matching opportunities or challenges.
    
    This workflow:
    1. Finds users who match certain criteria
    2. Gets relevant opportunities/challenges
    3. Sends personalized notifications
    """
    
    @workflow.run
    async def run(
        self,
        notification_type: str,  # "opportunity", "challenge", "reminder"
        criteria: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run the notification workflow.
        
        Args:
            notification_type: Type of notification to send
            criteria: Optional criteria for matching users
            
        Returns:
            Workflow result with notification details
        """
        # Get matching users based on criteria
        matching_users = await workflow.execute_activity(
            activities.get_matching_users,
            {
                "notification_type": notification_type,
                "criteria": criteria or {},
            },
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        # Get relevant content (opportunities/challenges)
        if notification_type == "opportunity":
            content = await workflow.execute_activity(
                activities.get_relevant_opportunities,
                criteria or {},
                start_to_close_timeout=timedelta(seconds=30),
            )
        elif notification_type == "challenge":
            content = await workflow.execute_activity(
                activities.get_active_challenges,
                start_to_close_timeout=timedelta(seconds=30),
            )
        else:
            content = []
        
        # Send notifications
        notification_results = []
        for user in matching_users:
            result = await workflow.execute_activity(
                activities.send_match_notification,
                {
                    "user_id": user["id"],
                    "user_phone": user["phone_number"],
                    "notification_type": notification_type,
                    "content": content,
                },
                start_to_close_timeout=timedelta(seconds=30),
            )
            notification_results.append(result)
        
        return {
            "notification_type": notification_type,
            "users_notified": len(matching_users),
            "content_items": len(content),
            "notification_results": notification_results,
        }


# Activities are imported from activities module
# They are referenced by name in workflow.execute_activity()


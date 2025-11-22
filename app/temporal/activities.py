"""Temporal activities for Chip.

Activities are the actual work that gets done - they interact with Supabase, send messages, etc.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.services.supabase_rag import get_rag_service
from app.services.user_service import get_user_service
from app.adapters.registry import AdapterRegistry
from app.types import IMessageTextMessage


async def get_or_create_weekly_challenge(week_number: int) -> str:
    """Get or create a weekly challenge for the given week.
    
    Args:
        week_number: Week number (1-6)
        
    Returns:
        Challenge ID (UUID as string)
    """
    rag_service = get_rag_service()
    
    if not rag_service.is_available():
        raise RuntimeError("Supabase not available")
    
    try:
        # Check if challenge for this week already exists
        # For now, we'll get the most recent weekly challenge
        # In production, you'd want to track week numbers
        challenges = rag_service.get_challenges(limit=1)
        
        if challenges and len(challenges) > 0:
            return challenges[0].id
        
        # If no challenge exists, create one
        # This is a simplified version - in production, you'd want more logic
        client = rag_service.client
        new_challenge = client.table("challenges").insert({
            "title": f"Week {week_number} Challenge",
            "description": f"This is week {week_number} of the 6-week Challenge Project. Complete the challenge and share your progress!",
            "type": "weekly",
            "deadline": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        }).execute()
        
        if new_challenge.data and len(new_challenge.data) > 0:
            return str(new_challenge.data[0]["id"])
        
        raise RuntimeError("Failed to create challenge")
        
    except Exception as e:
        print(f"Error in get_or_create_weekly_challenge: {e}")
        raise


async def get_active_users() -> List[Dict[str, Any]]:
    """Get all active users who should receive notifications.
    
    Returns:
        List of user dicts with id and phone_number
    """
    user_service = get_user_service()
    
    if not user_service.is_available():
        return []
    
    try:
        client = user_service.client
        response = client.table("users").select("id, phone_number, name").eq("is_active", True).execute()
        
        users = []
        for user in (response.data or []):
            users.append({
                "id": str(user["id"]),
                "phone_number": user["phone_number"],
                "name": user.get("name"),
            })
        
        return users
        
    except Exception as e:
        print(f"Error in get_active_users: {e}")
        return []


async def send_challenge_notification(data: Dict[str, Any]) -> Dict[str, Any]:
    """Send a challenge notification to a user.
    
    Args:
        data: Dict with user_id, user_phone, challenge_id, week_number
        
    Returns:
        Result dict with success status
    """
    user_phone = data.get("user_phone")
    challenge_id = data.get("challenge_id")
    week_number = data.get("week_number", 1)
    
    if not user_phone:
        return {"success": False, "error": "No phone number"}
    
    try:
        # Get challenge details
        rag_service = get_rag_service()
        if rag_service.is_available():
            client = rag_service.client
            challenge_response = client.table("challenges").select("*").eq("id", challenge_id).execute()
            
            if challenge_response.data and len(challenge_response.data) > 0:
                challenge = challenge_response.data[0]
                challenge_title = challenge.get("title", f"Week {week_number} Challenge")
                challenge_desc = challenge.get("description", "")
            else:
                challenge_title = f"Week {week_number} Challenge"
                challenge_desc = "Complete this week's challenge and share your progress!"
        else:
            challenge_title = f"Week {week_number} Challenge"
            challenge_desc = "Complete this week's challenge and share your progress!"
        
        # Create notification message
        message_text = (
            f"🎯 New Weekly Challenge!\n\n"
            f"{challenge_title}\n\n"
            f"{challenge_desc}\n\n"
            f"Reply with your submission when you're done!"
        )
        
        # Send via Loop (preferred for iMessage) or Twilio (SMS)
        # Try Loop first, fallback to Twilio
        adapter = None
        try:
            adapter = AdapterRegistry.get("loop")
        except:
            try:
                adapter = AdapterRegistry.get("twilio")
            except:
                return {"success": False, "error": "No messaging adapter available"}
        
        result = adapter.send_message(
            IMessageTextMessage(
                recipient=user_phone,
                text=message_text,
            )
        )
        
        return {
            "success": result.ok,
            "user_phone": user_phone,
            "message_id": result.message_id,
        }
        
    except Exception as e:
        print(f"Error in send_challenge_notification: {e}")
        return {"success": False, "error": str(e)}


async def get_matching_users(criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get users matching certain criteria.
    
    Args:
        criteria: Dict with criteria (e.g., {"has_submissions": True})
        
    Returns:
        List of matching user dicts
    """
    user_service = get_user_service()
    
    if not user_service.is_available():
        return []
    
    try:
        client = user_service.client
        
        # Build query based on criteria
        query = client.table("users").select("id, phone_number, name").eq("is_active", True)
        
        # Add criteria filters
        if criteria.get("has_submissions"):
            # Get users who have submissions
            # This would require a join or subquery in production
            # For now, get all active users
            pass
        
        response = query.execute()
        
        users = []
        for user in (response.data or []):
            users.append({
                "id": str(user["id"]),
                "phone_number": user["phone_number"],
                "name": user.get("name"),
            })
        
        return users
        
    except Exception as e:
        print(f"Error in get_matching_users: {e}")
        return []


async def get_relevant_opportunities(criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get relevant opportunities based on criteria.
    
    Args:
        criteria: Dict with criteria (e.g., {"type": "internship", "location": "Birmingham"})
        
    Returns:
        List of opportunity dicts
    """
    rag_service = get_rag_service()
    
    if not rag_service.is_available():
        return []
    
    try:
        opportunities = rag_service.get_opportunities(limit=10)
        
        # Filter based on criteria
        filtered = []
        for opp in opportunities:
            if criteria.get("type") and opp.type != criteria["type"]:
                continue
            if criteria.get("location") and criteria["location"].lower() not in opp.location.lower():
                continue
            
            filtered.append({
                "id": opp.id,
                "title": opp.title,
                "company": opp.company,
                "description": opp.description,
                "location": opp.location,
                "type": opp.type,
            })
        
        return filtered
        
    except Exception as e:
        print(f"Error in get_relevant_opportunities: {e}")
        return []


async def get_active_challenges() -> List[Dict[str, Any]]:
    """Get active challenges.
    
    Returns:
        List of challenge dicts
    """
    rag_service = get_rag_service()
    
    if not rag_service.is_available():
        return []
    
    try:
        challenges = rag_service.get_challenges(limit=10)
        
        return [
            {
                "id": challenge.id,
                "title": challenge.title,
                "description": challenge.description,
                "deadline": challenge.deadline,
                "type": challenge.type,
            }
            for challenge in challenges
        ]
        
    except Exception as e:
        print(f"Error in get_active_challenges: {e}")
        return []


async def send_match_notification(data: Dict[str, Any]) -> Dict[str, Any]:
    """Send a match notification to a user (opportunities/challenges).
    
    Args:
        data: Dict with user_id, user_phone, notification_type, content
        
    Returns:
        Result dict with success status
    """
    user_phone = data.get("user_phone")
    notification_type = data.get("notification_type")
    content = data.get("content", [])
    
    if not user_phone:
        return {"success": False, "error": "No phone number"}
    
    try:
        # Build notification message
        if notification_type == "opportunity" and content:
            message_text = "🎯 New Opportunities for You!\n\n"
            for i, opp in enumerate(content[:5], 1):  # Limit to 5
                message_text += f"{i}. {opp['title']} at {opp['company']} ({opp['location']})\n"
            message_text += "\nReply for more details!"
            
        elif notification_type == "challenge" and content:
            message_text = "🎯 New Challenges Available!\n\n"
            for i, challenge in enumerate(content[:3], 1):  # Limit to 3
                message_text += f"{i}. {challenge['title']}\n"
                if challenge.get('description'):
                    message_text += f"   {challenge['description'][:100]}...\n"
            message_text += "\nReply to participate!"
            
        else:
            message_text = "You have new updates! Reply to see what's new."
        
        # Send via Loop or Twilio
        adapter = None
        try:
            adapter = AdapterRegistry.get("loop")
        except:
            try:
                adapter = AdapterRegistry.get("twilio")
            except:
                return {"success": False, "error": "No messaging adapter available"}
        
        result = adapter.send_message(
            IMessageTextMessage(
                recipient=user_phone,
                text=message_text,
            )
        )
        
        return {
            "success": result.ok,
            "user_phone": user_phone,
            "message_id": result.message_id,
        }
        
    except Exception as e:
        print(f"Error in send_match_notification: {e}")
        return {"success": False, "error": str(e)}





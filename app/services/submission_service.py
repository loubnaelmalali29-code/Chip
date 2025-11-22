"""Submission service for managing challenge submissions in Supabase."""

import os
from typing import Optional, List, Dict, Any
from uuid import UUID

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False


class SubmissionService:
    """Service for managing challenge submissions."""
    
    def __init__(self):
        """Initialize the Supabase client."""
        self.client: Optional[Client] = None
        self._initialized = False
        
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if HAS_SUPABASE and supabase_url and supabase_key:
            try:
                self.client = create_client(supabase_url, supabase_key)
                self._initialized = True
                print("Submission service initialized successfully")
            except Exception as e:
                print(f"Warning: Failed to initialize Supabase client: {e}")
                self._initialized = False
        else:
            if not HAS_SUPABASE:
                print("Warning: supabase package not installed. Install with: pip install supabase")
            else:
                print("Warning: Supabase credentials not found.")
            self._initialized = False
    
    def is_available(self) -> bool:
        """Check if Supabase is available."""
        return self._initialized and self.client is not None
    
    def create_submission(
        self,
        user_id: UUID,
        challenge_id: UUID,
        submission_text: str,
        submission_url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new challenge submission.
        
        Args:
            user_id: User's UUID
            challenge_id: Challenge's UUID
            submission_text: Submission text from user
            submission_url: Optional URL (GitHub, portfolio, etc.)
            
        Returns:
            Submission dict if successful, None otherwise
        """
        if not self.is_available():
            print(f"Warning: Supabase not available. Cannot create submission.")
            return None
        
        try:
            # Use upsert to handle the UNIQUE constraint (user_id, challenge_id)
            # This will update if submission already exists, or create if new
            response = self.client.table("submissions").upsert({
                "user_id": str(user_id),
                "challenge_id": str(challenge_id),
                "submission_text": submission_text,
                "submission_url": submission_url,
                "status": "pending",  # Default status
            }).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
            
        except Exception as e:
            print(f"Error creating submission: {e}")
            return None
    
    def get_user_submissions(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get all submissions for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of submission dicts
        """
        if not self.is_available():
            return []
        
        try:
            response = self.client.table("submissions").select("*").eq("user_id", str(user_id)).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting user submissions: {e}")
            return []
    
    def get_challenge_submissions(self, challenge_id: UUID) -> List[Dict[str, Any]]:
        """Get all submissions for a challenge.
        
        Args:
            challenge_id: Challenge's UUID
            
        Returns:
            List of submission dicts
        """
        if not self.is_available():
            return []
        
        try:
            response = self.client.table("submissions").select("*").eq("challenge_id", str(challenge_id)).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting challenge submissions: {e}")
            return []


# Global submission service instance (singleton)
_submission_service: Optional[SubmissionService] = None


def get_submission_service() -> SubmissionService:
    """Get or create the submission service instance.
    
    Returns:
        SubmissionService instance
    """
    global _submission_service
    if _submission_service is None:
        _submission_service = SubmissionService()
    return _submission_service





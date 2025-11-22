"""User service for managing users in Supabase.

This service handles user lookup and creation using the get_or_create_user function.
"""

import os
from typing import Optional
from uuid import UUID

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False


class UserService:
    """Service for managing users in Supabase."""
    
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
                print("User service initialized successfully")
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
    
    def get_or_create_user(
        self,
        phone_number: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[UUID]:
        """Get or create a user by phone number.
        
        Uses the get_or_create_user() SQL function in Supabase.
        
        Args:
            phone_number: User's phone number (from webhook)
            name: Optional user name
            email: Optional user email
            
        Returns:
            User ID (UUID) if successful, None otherwise
        """
        if not self.is_available():
            print(f"Warning: Supabase not available. Cannot get/create user for {phone_number}")
            return None
        
        try:
            # Call the get_or_create_user function
            # This is a PostgreSQL function, so we use RPC (Remote Procedure Call)
            response = self.client.rpc(
                "get_or_create_user",
                {
                    "p_phone_number": phone_number,
                    "p_name": name,
                    "p_email": email,
                }
            ).execute()
            
            # The function returns a UUID
            user_id = response.data
            if isinstance(user_id, str):
                return UUID(user_id)
            return user_id
            
        except Exception as e:
            print(f"Error getting/creating user: {e}")
            # Fallback: try to query users table directly
            try:
                # Try to find existing user
                existing = self.client.table("users").select("id").eq("phone_number", phone_number).execute()
                if existing.data and len(existing.data) > 0:
                    user_id = existing.data[0]["id"]
                    return UUID(user_id) if isinstance(user_id, str) else user_id
                
                # Create new user
                new_user = self.client.table("users").insert({
                    "phone_number": phone_number,
                    "name": name,
                    "email": email,
                }).execute()
                
                if new_user.data and len(new_user.data) > 0:
                    user_id = new_user.data[0]["id"]
                    return UUID(user_id) if isinstance(user_id, str) else user_id
            except Exception as e2:
                print(f"Error in fallback user creation: {e2}")
            
            return None
    
    def get_user_by_phone(self, phone_number: str) -> Optional[dict]:
        """Get user by phone number.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            User dict if found, None otherwise
        """
        if not self.is_available():
            return None
        
        try:
            response = self.client.table("users").select("*").eq("phone_number", phone_number).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error getting user by phone: {e}")
            return None


# Global user service instance (singleton)
_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    """Get or create the user service instance.
    
    Returns:
        UserService instance
    """
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service





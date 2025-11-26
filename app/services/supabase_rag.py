"""Supabase RAG (Retrieval Augmented Generation) service for Chip.

This service provides data retrieval from Supabase for the RAG pipeline.
Even though full Supabase integration is TSP-5, we need basic RAG functionality
for TSP-3 to pull opportunities, challenges, and user data.
"""

import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False


@dataclass
class Opportunity:
    """Opportunity data structure."""
    id: str
    title: str
    company: str
    description: str
    location: str
    type: str  # job, internship, etc.


@dataclass
class Job:
    """Job listing data structure."""
    id: str
    title: str
    company: str
    description: str
    location: str
    salary_range: Optional[str]
    employment_type: str  # full-time, part-time, contract, etc.
    application_url: Optional[str]


@dataclass
class Challenge:
    """Challenge data structure."""
    id: str
    title: str
    description: str
    deadline: Optional[str]
    type: str  # weekly, hackathon, etc.


class SupabaseRAGService:
    """Service for retrieving data from Supabase for RAG."""
    
    def __init__(self):
        """Initialize the Supabase client."""
        self.client: Optional[Client] = None
        self._initialized = False
        
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if HAS_SUPABASE and supabase_url and supabase_key:
            try:
                self.client = create_client(supabase_url, supabase_key)
                self._initialized = True
                print("Supabase RAG service initialized successfully")
            except Exception as e:
                print(f"Warning: Failed to initialize Supabase client: {e}")
                self._initialized = False
        else:
            if not HAS_SUPABASE:
                print("Warning: supabase package not installed. Install with: pip install supabase")
            else:
                print("Warning: Supabase credentials not found. RAG will use mock data.")
            self._initialized = False
    
    def is_available(self) -> bool:
        """Check if Supabase is available."""
        return self._initialized and self.client is not None
    
    def get_opportunities(self, limit: int = 5) -> List[Opportunity]:
        """Get opportunities from Supabase.
        
        Args:
            limit: Maximum number of opportunities to return
            
        Returns:
            List of opportunities
        """
        # In production we never want to surface fake data.
        # If Supabase is unavailable, return an empty list and let the agent
        # explain that data is temporarily unavailable.
        if not self.is_available():
            return []
        
        try:
            response = self.client.table("opportunities").select("*").limit(limit).execute()
            
            opportunities = []
            for item in response.data:
                opportunities.append(Opportunity(
                    id=str(item.get("id", "")),
                    title=item.get("title", "Unknown"),
                    company=item.get("company", "Unknown"),
                    description=item.get("description", ""),
                    location=item.get("location", "Alabama"),
                    type=item.get("type", "job"),
                ))
            
            return opportunities
            
        except Exception as e:
            print(f"Error fetching opportunities from Supabase: {e}")
            return self._get_mock_opportunities(limit)
    
    
    def get_challenges(self, limit: int = 5) -> List[Challenge]:
        """Get challenges from Supabase.
        
        Args:
            limit: Maximum number of challenges to return
            
        Returns:
            List of challenges
        """
        # In production we never want to surface fake data.
        # If Supabase is unavailable, return an empty list and let the agent
        # explain that data is temporarily unavailable.
        if not self.is_available():
            return []
        
        try:
            response = self.client.table("challenges").select("*").limit(limit).execute()
            
            challenges = []
            for item in response.data:
                # Ensure ID is properly formatted as string
                challenge_id = item.get("id")
                if challenge_id:
                    challenge_id = str(challenge_id)
                else:
                    challenge_id = ""
                
                challenges.append(Challenge(
                    id=challenge_id,
                    title=item.get("title", "Unknown"),
                    description=item.get("description", ""),
                    deadline=item.get("deadline"),
                    type=item.get("type", "weekly"),
                ))
            
            return challenges
            
        except Exception as e:
            print(f"Error fetching challenges from Supabase: {e}")
            return self._get_mock_challenges(limit)
    
    def get_context_for_query(self, query: str) -> str:
        """Get relevant context for a user query.
        
        This is the main RAG function - it retrieves relevant data based on the query.
        
        Args:
            query: User's query
            
        Returns:
            Context string with relevant data
        """
        query_lower = query.lower()
        context_parts = []
        
        if any(word in query_lower for word in ["job", "jobs", "employment", "hire", "hiring", "career", "position", "opening", "opportunit", "intern", "internship"]):
            opportunities = self.get_opportunities(limit=5)
            if opportunities:
                context_parts.append("Opportunities:")
                for opp in opportunities:
                    context_parts.append(f"- {opp.title} at {opp.company} ({opp.location}) - {opp.type}")
                    if opp.description:
                        context_parts.append(f"  Description: {opp.description}")
        
        # Check if query is about challenges
        if any(word in query_lower for word in ["challenge", "project", "hackathon", "competition"]):
            challenges = self.get_challenges(limit=5)
            if challenges:
                context_parts.append("Challenges:")
                for challenge in challenges:
                    # Include challenge ID for submission linking
                    context_parts.append(f"- {challenge.title} (ID: {challenge.id}): {challenge.description}")
        
        return "\n".join(context_parts) if context_parts else "No specific context available."
    
    def _get_mock_opportunities(self, limit: int = 5) -> List[Opportunity]:
        """Get mock opportunities when Supabase is not available."""
        return [
            Opportunity(
                id="1",
                title="Software Engineering Intern",
                company="TechCorp",
                description="Join our engineering team for a summer internship",
                location="Birmingham, AL",
                type="internship",
            ),
            Opportunity(
                id="2",
                title="Data Scientist",
                company="DataCo",
                description="Work on cutting-edge data science projects",
                location="Huntsville, AL",
                type="job",
            ),
            Opportunity(
                id="3",
                title="Full Stack Developer",
                company="StartupXYZ",
                description="Build web applications using modern technologies",
                location="Montgomery, AL",
                type="job",
            ),
        ][:limit]
    
    def _get_mock_jobs(self, limit: int = 5) -> List[Job]:
        """Get mock jobs when Supabase is not available."""
        return [
            Job(
                id="1",
                title="Senior Software Engineer",
                company="TechCorp",
                description="Lead development of cutting-edge software solutions",
                location="Birmingham, AL",
                salary_range="$100,000 - $150,000",
                employment_type="full-time",
                application_url="https://example.com/apply",
            ),
            Job(
                id="2",
                title="Data Scientist",
                company="DataCo",
                description="Work on machine learning and data analytics projects",
                location="Huntsville, AL",
                salary_range="$90,000 - $130,000",
                employment_type="full-time",
                application_url="https://example.com/apply",
            ),
            Job(
                id="3",
                title="Full Stack Developer",
                company="StartupXYZ",
                description="Build scalable web applications",
                location="Montgomery, AL",
                salary_range="$80,000 - $120,000",
                employment_type="full-time",
                application_url="https://example.com/apply",
            ),
        ][:limit]
    
    def _get_mock_challenges(self, limit: int = 5) -> List[Challenge]:
        """Get mock challenges when Supabase is not available."""
        return [
            Challenge(
                id="1",
                title="Weekly Coding Challenge: Build a REST API",
                description="Build a REST API using your favorite framework",
                deadline="2024-12-01",
                type="weekly",
            ),
            Challenge(
                id="2",
                title="Hackathon: Innovation in Birmingham",
                description="48-hour hackathon focused on innovation",
                deadline="2024-12-15",
                type="hackathon",
            ),
            Challenge(
                id="3",
                title="Career Fair Challenge: Network with 10 people",
                description="Network with 10 people at the career fair",
                deadline="2024-11-30",
                type="event",
            ),
        ][:limit]


# Global RAG service instance (singleton)
_rag_service: Optional[SupabaseRAGService] = None


def get_rag_service() -> SupabaseRAGService:
    """Get or create the RAG service instance.
    
    Returns:
        SupabaseRAGService instance
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = SupabaseRAGService()
    return _rag_service


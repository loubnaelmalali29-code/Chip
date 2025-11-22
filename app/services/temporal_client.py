"""Temporal client service for Chip.

This service manages the Temporal client connection and provides access to workflows.
"""

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


class TemporalService:
    """Service for managing Temporal client connection."""
    
    def __init__(self):
        """Initialize the Temporal service."""
        self.client: Optional[TemporalClient] = None
        self.worker: Optional[Worker] = None
        self._initialized = False
        
        # Get Temporal configuration
        temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
        temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
        
        self.host = temporal_host
        self.namespace = temporal_namespace
    
    async def connect(self) -> None:
        """Connect to Temporal server."""
        if not HAS_TEMPORAL:
            print("Warning: temporalio package not installed. Install with: pip install temporalio")
            return
        
        if self._initialized:
            return
        
        try:
            # Connect to Temporal server
            # For local development, default is localhost:7233
            self.client = await TemporalClient.connect(
                target_host=self.host,
                namespace=self.namespace,
            )
            self._initialized = True
            print(f"Temporal client connected to {self.host}/{self.namespace}")
        except Exception as e:
            print(f"Warning: Failed to connect to Temporal: {e}")
            print("Note: Make sure Temporal server is running locally (temporal server start-dev)")
            self._initialized = False
    
    async def close(self) -> None:
        """Close Temporal client connection."""
        if self.client:
            await self.client.close()
            self._initialized = False
            print("Temporal client closed")
    
    def is_available(self) -> bool:
        """Check if Temporal is available."""
        return self._initialized and self.client is not None
    
    def get_client(self) -> Optional[TemporalClient]:
        """Get the Temporal client instance."""
        return self.client if self.is_available() else None


# Global Temporal service instance (singleton)
_temporal_service: Optional[TemporalService] = None


def get_temporal_service() -> TemporalService:
    """Get or create the Temporal service instance.
    
    Returns:
        TemporalService instance
    """
    global _temporal_service
    if _temporal_service is None:
        _temporal_service = TemporalService()
    return _temporal_service





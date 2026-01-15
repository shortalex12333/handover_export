"""
Dependency injection for FastAPI routes
"""
from typing import Optional
from fastapi import HTTPException

from .graph.client import GraphClient
from .ai.openai_client import OpenAIClient
from .db.supabase_client import SupabaseClient

# Global client instances (set by main.py lifespan)
_graph_client: Optional[GraphClient] = None
_openai_client: Optional[OpenAIClient] = None
_db_client: Optional[SupabaseClient] = None


def set_graph_client(client: GraphClient):
    """Set global graph client instance"""
    global _graph_client
    _graph_client = client


def set_openai_client(client: OpenAIClient):
    """Set global OpenAI client instance"""
    global _openai_client
    _openai_client = client


def set_db_client(client: SupabaseClient):
    """Set global database client instance"""
    global _db_client
    _db_client = client


# Dependency functions for FastAPI
def get_graph_client() -> GraphClient:
    """Get Graph client for dependency injection"""
    if not _graph_client:
        raise HTTPException(500, "Graph client not configured")
    return _graph_client


def get_openai_client() -> OpenAIClient:
    """Get OpenAI client for dependency injection"""
    if not _openai_client:
        raise HTTPException(500, "OpenAI client not configured")
    return _openai_client


def get_db_client() -> SupabaseClient:
    """Get database client for dependency injection"""
    if not _db_client:
        raise HTTPException(500, "Database client not configured")
    return _db_client


# Mock user auth (replace with actual auth)
async def get_current_user() -> dict:
    """
    Get current authenticated user from JWT token

    In production, this should:
    1. Extract JWT from Authorization header
    2. Validate signature
    3. Decode user_id and yacht_id
    4. Fetch user profile from database
    5. Return user context
    """
    # TODO: Implement actual JWT auth
    return {
        "id": "00000000-0000-0000-0000-000000000000",
        "yacht_id": "00000000-0000-0000-0000-000000000000",
        "role": "Captain",
        "department": "Command"
    }

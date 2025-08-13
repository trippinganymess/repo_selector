from fastapi import HTTPException, Header, Depends
from typing import Optional
import os
import requests
from src.github_client import GitHubClient
from src.repo_analyzer import RepositoryAnalyzer  
from src.database import RepositoryDatabase
from src.config import GITHUB_TOKEN

async def get_github_client() -> GitHubClient:
    """Dependency to get GitHub client"""
    if not GITHUB_TOKEN:
        raise HTTPException(status_code=500, detail="GitHub token not configured")
    return GitHubClient()

async def get_repository_analyzer() -> RepositoryAnalyzer:
    """Dependency to get repository analyzer with full comprehensive functionality"""
    return RepositoryAnalyzer()

async def get_database(user_id: Optional[str] = None) -> RepositoryDatabase:
    """Dependency to get user-specific database"""
    return RepositoryDatabase(user_id=user_id)

async def get_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from header or generate default"""
    return x_user_id or f"api_user_{os.getenv('USER', 'unknown')}"

async def validate_repo_format(owner: str, repo: str):
    """Validate repository owner/name format"""
    if not owner or not repo or '/' in owner or '/' in repo:
        raise HTTPException(
            status_code=400, 
            detail="Invalid repository format. Use owner and repo as separate path parameters."
        )
    return True

async def check_github_api_health() -> dict:
    """Check GitHub API connectivity and rate limits"""
    try:
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
        response = requests.get("https://api.github.com/rate_limit", headers=headers, timeout=5)
        
        if response.status_code == 200:
            rate_data = response.json()
            remaining = rate_data.get('rate', {}).get('remaining', 0)
            
            if remaining < 100:
                return {"status": "limited", "remaining": remaining}
            else:
                return {"status": "ok", "remaining": remaining}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def check_database_health(user_id: str = "health_check") -> dict:
    """Check database connectivity"""
    try:
        db = RepositoryDatabase(user_id=user_id)
        stats = db.get_statistics()
        return {"status": "ok", "stats": stats}
    except Exception as e:
        return {"status": "error", "message": str(e)}

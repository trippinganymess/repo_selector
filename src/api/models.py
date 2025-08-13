from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Request Models
class SearchRequest(BaseModel):
    min_stars: int = Field(default=500, ge=0, description="Minimum star count")
    max_stars: int = Field(default=50000, le=100000, description="Maximum star count") 
    limit: int = Field(default=30, ge=1, le=100, description="Maximum repositories to return")
    days_filter: int = Field(default=7, ge=0, description="Filter repos shown in last N days")
    fresh_only: bool = Field(default=True, description="Only show repos user hasn't seen")
    force_refresh: bool = Field(default=False, description="Ignore all filtering")
    user_id: Optional[str] = Field(default=None, description="User identifier")

class ExportRequest(BaseModel):
    format: str = Field(default="json", pattern=r"^(json|csv|yaml|markdown)$")
    user_id: Optional[str] = None

# Response Models
class Repository(BaseModel):
    repo_name: str
    stars: int
    license: str
    py_files_estimate: int
    python_percentage: str
    url: str
    description: str
    passes_criteria: bool
    is_new: bool = True

class SearchResponse(BaseModel):
    success: bool
    message: str
    repositories: List[Repository]
    user_id: str
    total_found: int
    rate_limit_remaining: int
    search_criteria: Dict[str, Any]
    database_stats: Optional[Dict[str, Any]] = None

class OpportunityItem(BaseModel):
    type: str
    title: str
    url: str

class AnalysisResponse(BaseModel):
    success: bool
    repository: str
    score: float
    max_score: float = 5
    percentage: float
    is_suitable: bool
    recommendation: str
    reasons: List[str]
    warnings: List[str]
    repository_info: Dict[str, Any]
    # Comprehensive analysis fields
    activity_score: Optional[float] = None
    opportunity_score: Optional[float] = None
    complexity_score: Optional[float] = None
    maintainability_score: Optional[float] = None
    opportunities: Optional[List[OpportunityItem]] = None

class UserStats(BaseModel):
    user_id: str
    total_repositories: int
    passing_repositories: int
    recent_repositories: int
    total_searches: int

class ExportResponse(BaseModel):
    success: bool
    message: str
    file_url: Optional[str] = None
    export_info: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime
    version: str
    github_api_status: str
    database_status: str

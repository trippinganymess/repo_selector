from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List
import asyncio
from datetime import datetime

from .models import *
from .dependencies import *
from src.github_client import GitHubClient
from src.repo_analyzer import RepositoryAnalyzer
from src.database import RepositoryDatabase
from src.dataBaseExporter import DatabaseExporter
from src import __version__

router = APIRouter(prefix="/api/v1", tags=["repository-selector"])

@router.post("/search", response_model=SearchResponse)
async def search_repositories(
    request: SearchRequest,
    github_client: GitHubClient = Depends(get_github_client),
    analyzer: RepositoryAnalyzer = Depends(get_repository_analyzer),
    user_id: str = Depends(get_user_id)
):
    """Search for Python repositories suitable for SWE Challenge V3"""
    
    try:
        # Use user_id from request if provided
        if request.user_id:
            user_id = request.user_id
        
        db = RepositoryDatabase(user_id=user_id)
        
        # Search with multiple attempts for fresh results
        all_candidates = []
        search_offset = 0
        
        max_attempts = 3 if request.fresh_only and not request.force_refresh else 1
        rate_limit_remaining = 5000  # Default
        
        for attempt in range(max_attempts):
            current_offset = search_offset + (attempt * request.limit)
            
            # Use enhanced search if available
            if hasattr(github_client, 'search_with_randomization'):
                search_result = github_client.search_with_randomization(
                    request.min_stars, request.max_stars, request.limit, current_offset
                )
            else:
                search_result = github_client.search_repositories_graphql(
                    request.min_stars, request.max_stars, request.limit
                )
            
            repos = search_result['repositories']
            rate_limit_remaining = search_result['rate_limit']['remaining']
            
            if not repos:
                continue
            
            # Analyze repositories
            results = analyzer.analyze_repositories_fast(repos)
            good_candidates = analyzer.filter_good_candidates(results)
            
            if not good_candidates:
                continue
            
            # Apply freshness filtering
            if not request.force_refresh and request.fresh_only:
                good_candidates = db.filter_new_repositories(good_candidates, request.days_filter)
            
            all_candidates.extend(good_candidates)
            
            if len(all_candidates) >= 3 or request.force_refresh:
                break
        
        # Remove duplicates
        seen = set()
        unique_candidates = []
        for repo in all_candidates:
            if repo['repo_name'] not in seen:
                seen.add(repo['repo_name'])
                repo['is_new'] = True
                unique_candidates.append(repo)
        
        # Save to database
        if unique_candidates:
            search_criteria = {
                'min_stars': request.min_stars,
                'max_stars': request.max_stars, 
                'limit': request.limit
            }
            db.add_repositories(unique_candidates, search_criteria, search_offset)
        
        # Convert to response format
        repositories = [Repository(**repo) for repo in unique_candidates]
        
        # Get database statistics
        db_stats = db.get_statistics()
        
        return SearchResponse(
            success=True,
            message=f"Found {len(repositories)} repositories",
            repositories=repositories,
            user_id=user_id,
            total_found=len(repositories),
            rate_limit_remaining=rate_limit_remaining,
            search_criteria=request.dict(),
            database_stats=db_stats
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/analyze/{owner}/{repo}", response_model=AnalysisResponse)
async def analyze_repository(
    owner: str,
    repo: str,
    analyzer: RepositoryAnalyzer = Depends(get_repository_analyzer),
    _: bool = Depends(validate_repo_format)
):
    """Analyze repository suitability for SWE Challenge V3 using comprehensive analysis"""
    
    try:
        # Use your comprehensive CLI analyzer instead of basic analysis
        analysis = analyzer.analyze_repository_deep(owner, repo)
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Repository {owner}/{repo} not found")
        
        # Check if analysis failed
        if analysis.get('warnings') and any('Could not fetch repository data' in w for w in analysis['warnings']):
            raise HTTPException(status_code=404, detail=f"Repository {owner}/{repo} not found")
        
        # Convert opportunities to proper format
        opportunities = []
        if analysis.get('opportunities'):
            opportunities = [
                OpportunityItem(
                    type=opp.get('type', 'Unknown'),
                    title=opp.get('title', 'No title'),
                    url=opp.get('url', '#')
                ) for opp in analysis['opportunities']
            ]
        
        # Convert CLI analysis format to API response format
        return AnalysisResponse(
            success=True,
            repository=f"{owner}/{repo}",
            score=round(analysis['overall_score'], 1),
            percentage=round((analysis['overall_score'] / 5) * 100, 1),
            is_suitable=analysis['is_suitable'],
            recommendation=analysis['recommendation'],
            reasons=analysis['reasons'],
            warnings=analysis.get('warnings', []),
            repository_info={
                "stars": analysis.get('stars', 0),
                "language": analysis.get('language', 'Unknown'),
                "license": analysis.get('license', 'Unknown'),
                "url": analysis.get('url', ''),
                "description": analysis.get('description', '')
            },
            activity_score=analysis['activity_score'],
            opportunity_score=analysis['opportunity_score'],
            complexity_score=analysis['complexity_score'],
            maintainability_score=analysis['maintainability_score'],
            opportunities=opportunities
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/users/{user_id}/stats", response_model=UserStats)
async def get_user_statistics(user_id: str):
    """Get user-specific repository statistics"""
    
    try:
        db = RepositoryDatabase(user_id=user_id)
        stats = db.get_statistics()
        
        return UserStats(
            user_id=stats.get('user_id', user_id),
            total_repositories=stats.get('total_repositories', 0),
            passing_repositories=stats.get('passing_repositories', 0),
            recent_repositories=stats.get('recent_repositories', 0),
            total_searches=stats.get('total_searches', 0)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@router.post("/export", response_model=ExportResponse)
async def export_database(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id)
):
    """Export user database to specified format"""
    
    try:
        if request.user_id:
            user_id = request.user_id
            
        db = RepositoryDatabase(user_id=user_id)
        exporter = DatabaseExporter(db.db_path)
        
        repositories = exporter.get_user_repositories(user_id)
        
        if not repositories:
            raise HTTPException(status_code=404, detail=f"No repositories found for user {user_id}")
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"repositories_{user_id}_{timestamp}.{request.format}"
        
        # Export based on format
        success = False
        if request.format == "json":
            success = exporter.export_to_json(repositories, filename)
        elif request.format == "csv":
            success = exporter.export_to_csv(repositories, filename)
        elif request.format == "yaml":
            success = exporter.export_to_yaml(repositories, filename)
        elif request.format == "markdown":
            success = exporter.export_to_markdown(repositories, filename)
        
        if not success:
            raise HTTPException(status_code=500, detail="Export failed")
        
        return ExportResponse(
            success=True,
            message=f"Database exported successfully to {filename}",
            file_url=f"/downloads/{filename}",  # You'd implement file serving
            export_info={
                "format": request.format,
                "total_repositories": len(repositories),
                "exported_at": datetime.now().isoformat(),
                "filename": filename
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """API health check with comprehensive status"""
    
    try:
        # Check GitHub API
        github_health = await check_github_api_health()
        github_status = github_health.get('status', 'unknown')
        
        # Check database
        db_health = await check_database_health()
        db_status = db_health.get('status', 'unknown')
        
        # Determine overall status
        overall_status = "healthy"
        if github_status == "error" or db_status == "error":
            overall_status = "unhealthy"
        elif github_status == "limited":
            overall_status = "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now(),
            version=__version__,
            github_api_status=github_status,
            database_status=db_status
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

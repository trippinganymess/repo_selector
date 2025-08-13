import typer
import sys
import os
from typing import List, Dict
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from .config import MIN_STARS, MAX_STARS, DEFAULT_LIMIT, DEFAULT_EXPORT_CSV, MIN_PY_FILES, MAX_PY_FILES, ALLOWED_LICENSES, GITHUB_TOKEN
    from .repo_analyzer import RepositoryAnalyzer
    from .github_client import GitHubClient
    from .database import RepositoryDatabase
    from .dataBaseExporter import DatabaseExporter
except ImportError:
    from config import MIN_STARS, MAX_STARS, DEFAULT_LIMIT, DEFAULT_EXPORT_CSV, MIN_PY_FILES, MAX_PY_FILES, ALLOWED_LICENSES, GITHUB_TOKEN
    from repo_analyzer import RepositoryAnalyzer
    from github_client import GitHubClient
    from database import RepositoryDatabase
    from dataBaseExporter import DatabaseExporter


console = Console()

# Create the app object that main.py expects
app = typer.Typer(help="GitHub Repository Selector for SWE Challenge V3")

def display_graphql_results(results: List[Dict], db_stats: Dict = None):
    """Display GraphQL results in a formatted way"""
    if not results:
        console.print("❌ No good candidates found", style="red")
        return
    
    console.print(f"✅ {len(results)} good candidates found")
    
    if db_stats:
        user_info = f" (User: {db_stats.get('user_id', 'unknown')})" if 'user_id' in db_stats else ""
        console.print(f"📊 Database: {db_stats['total_repositories']} total repos tracked, {db_stats['recent_repositories']} shown recently{user_info}\n")
    
    for i, repo in enumerate(results[:10], 1):
        repo_name = repo.get('repo_name', repo.get('name', 'Unknown'))
        stars = repo.get('stars', repo.get('star_count', 0))
        license_name = repo.get('license', 'Unknown')
        python_pct = repo.get('python_percentage', '0%')
        url = repo.get('url', '#')
        description = repo.get('description', '')
        
        # Check if this is a new repo
        is_new = "🆕" if repo.get('is_new', True) else "🔄"
        
        console.print(f"{i:2d}. {is_new} [cyan]{repo_name}[/cyan]")
        console.print(f"    ⭐ {stars:,} stars | 📜 {license_name} | 🐍 {python_pct} Python")
        console.print(f"    🔗 {url}")
        if description:
            console.print(f"    📝 {description}")
        console.print()

def export_to_csv(results: List[Dict], filename: str):
    """Export GraphQL results to CSV"""
    if not results:
        console.print("❌ No results to export", style="red")
        return
    
    try:
        import csv
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['repo_name', 'stars', 'license', 'py_files_estimate', 'python_percentage', 'url', 'passes_criteria', 'is_new']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                writer.writerow({
                    'repo_name': result.get('repo_name', ''),
                    'stars': result.get('stars', 0),
                    'license': result.get('license', ''),
                    'py_files_estimate': result.get('py_files_estimate', 0),
                    'python_percentage': result.get('python_percentage', ''),
                    'url': result.get('url', ''),
                    'passes_criteria': result.get('passes_criteria', False),
                    'is_new': result.get('is_new', True)
                })
        
        console.print(f"✅ Results exported to {filename}", style="green")
    except Exception as e:
        console.print(f"❌ Error exporting to CSV: {e}", style="red")

def normalize_license(license_name):
    """Normalize license names for comparison"""
    if not license_name:
        return ""
    return license_name.upper().replace('-', '').replace(' ', '').replace('_', '').replace('LICENSE', '').replace('V', '').replace('.', '').strip()

def check_license_compatibility(license_info):
    """Enhanced license compatibility check"""
    if not license_info:
        return False, "No license", ""
    
    license_name = license_info.get('name', '')
    license_spdx = license_info.get('spdx_id', '')
    
    license_mappings = {
        'APACHE LICENSE 2.0': 'Apache-2.0',
        'APACHE LICENSE': 'Apache-2.0',
        'APACHE 2.0': 'Apache-2.0',
        'APACHE2.0': 'Apache-2.0',
        'APACHE-2': 'Apache-2.0',
        'MIT LICENSE': 'MIT',
        'THE MIT LICENSE': 'MIT',
        'BSD 3-CLAUSE': 'BSD-3-Clause',
        'BSD 3 CLAUSE': 'BSD-3-Clause',
        'BSD3CLAUSE': 'BSD-3-Clause',
        'BSD 2-CLAUSE': 'BSD-2-Clause',
        'BSD 2 CLAUSE': 'BSD-2-Clause',
        'BSD2CLAUSE': 'BSD-2-Clause',
        'BOOST SOFTWARE LICENSE': 'BSL-1.0',
        'BOOST SOFTWARE LICENSE 1.0': 'BSL-1.0'
    }
    
    if license_spdx:
        for allowed in ALLOWED_LICENSES:
            if license_spdx.upper().replace('-', '').replace('_', '') == allowed.upper().replace('-', '').replace('_', ''):
                return True, license_spdx, allowed
    
    if license_name:
        normalized_name = normalize_license(license_name)
        
        if normalized_name in [normalize_license(k) for k in license_mappings.keys()]:
            for key, value in license_mappings.items():
                if normalized_name == normalize_license(key):
                    for allowed in ALLOWED_LICENSES:
                        if normalize_license(value) == normalize_license(allowed):
                            return True, license_name, allowed
        
        for allowed in ALLOWED_LICENSES:
            if normalized_name == normalize_license(allowed):
                return True, license_name, allowed
    
    return False, license_name or license_spdx or "Unknown", ""

@app.command()
def search(
    min_stars: int = typer.Option(MIN_STARS, "--min-stars", help="Minimum star count"),
    max_stars: int = typer.Option(MAX_STARS, "--max-stars", help="Maximum star count"),
    limit: int = typer.Option(DEFAULT_LIMIT, "--limit", help="Maximum repos to fetch"),
    days_filter: int = typer.Option(7, "--days-filter", help="Filter repos shown in last N days"),
    fresh_only: bool = typer.Option(True, "--fresh-only/--allow-repeats", help="Only show repos you haven't seen"),
    export_csv: bool = typer.Option(DEFAULT_EXPORT_CSV, "--export-csv", help="Export results to CSV"),
    force_refresh: bool = typer.Option(False, "--force-refresh", help="Show all repos, ignore recent filter")
):
    """Ultra-fast GitHub repository search with user-specific database tracking"""
    console.print("⚡ [bold]Ultra-Fast GitHub Search[/bold]", style="green")
    
    # Validate inputs
    if min_stars >= max_stars:
        console.print("❌ min-stars must be less than max-stars", style="red")
        return
    
    if limit <= 0 or limit > 100:
        console.print("❌ limit must be between 1 and 100", style="red")
        return
    
    # Initialize user-specific services
    github = GitHubClient()
    analyzer = RepositoryAnalyzer()
    db = RepositoryDatabase()  # Automatically uses current user
    
    # Get search offset for fresh results
    search_criteria = {'min_stars': min_stars, 'max_stars': max_stars, 'limit': limit}
    search_offset = db.get_last_search_offset(search_criteria) if hasattr(db, 'get_last_search_offset') else 0
    
    console.print(f"👤 User: {db.user_id if hasattr(db, 'user_id') else 'default'}")
    if search_offset > 0:
        console.print(f"🔄 Search offset: {search_offset} (for fresh GitHub results)")
    
    try:
        # Try multiple search strategies to get fresh results
        max_attempts = 3 if fresh_only and not force_refresh else 1
        all_candidates = []
        
        for attempt in range(max_attempts):
            current_offset = search_offset + (attempt * limit)
            
            with Progress(SpinnerColumn(), TextColumn("🚀 Searching GitHub for fresh repos...")) as progress:
                task = progress.add_task("Searching...", total=1)
                
                # Use enhanced search if available, otherwise fallback to standard
                if hasattr(github, 'search_with_randomization'):
                    search_result = github.search_with_randomization(min_stars, max_stars, limit, current_offset)
                else:
                    search_result = github.search_repositories_graphql(min_stars, max_stars, limit)
                
                progress.advance(task)
            
            repos = search_result['repositories']
            rate_limit = search_result['rate_limit']
            
            console.print(f"✅ Rate limit remaining: {rate_limit['remaining']} (cost: {rate_limit['cost']})")
            
            if not repos:
                console.print("❌ No repositories found with those criteria", style="yellow")
                continue
            
            console.print(f"📊 Found {len(repos)} repositories from GitHub")
            
            # Analyze repositories
            results = analyzer.analyze_repositories_fast(repos)
            good_candidates = analyzer.filter_good_candidates(results)
            
            if not good_candidates:
                console.print("⚠️ No repositories passed quality criteria", style="yellow")
                continue
            
            # Filter out recently shown repositories (unless force_refresh)
            if not force_refresh and (fresh_only or attempt == 0):
                original_count = len(good_candidates)
                fresh_candidates = db.filter_new_repositories(good_candidates, days_filter)
                
                if len(fresh_candidates) < original_count:
                    filtered_count = original_count - len(fresh_candidates)
                    console.print(f"🔄 Filtered out {filtered_count} repos you've seen before (last {days_filter} days)")
                
                all_candidates.extend(fresh_candidates)
            else:
                all_candidates.extend(good_candidates)
            
            # If we have enough fresh results, stop searching
            if len(all_candidates) >= 3 or force_refresh:
                break
            
            if attempt < max_attempts - 1:
                console.print(f"🔍 Attempt {attempt + 1}: Found {len(good_candidates)} quality repos, {len(fresh_candidates if fresh_only else good_candidates)} fresh. Trying different search...")
        
        if not all_candidates:
            console.print("❌ No fresh repositories found. Try adjusting your search parameters.", style="yellow")
            console.print("💡 Try: --allow-repeats to see repos you've seen before", style="blue")
            console.print("💡 Or: --force-refresh to ignore all filtering", style="blue")
            console.print("💡 Or: change --min-stars and --max-stars range", style="blue")
            return
        
        # Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for repo in all_candidates:
            if repo['repo_name'] not in seen:
                seen.add(repo['repo_name'])
                repo['is_new'] = True  # Mark as new for this search
                unique_candidates.append(repo)
        
        # Save to user-specific database
        if unique_candidates:
            db.add_repositories(unique_candidates, search_criteria, search_offset)
        
        # Get database statistics
        db_stats = db.get_statistics()
        
        # Display results
        console.print(f"✅ Found {len(unique_candidates)} fresh repositories for you!")
        display_graphql_results(unique_candidates, db_stats)
        
        # Export if requested
        if export_csv:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            user_id = db.user_id if hasattr(db, 'user_id') else 'user'
            filename = f"fresh_repos_{user_id}_{timestamp}.csv"
            export_to_csv(unique_candidates, filename)
        
    except Exception as e:
        console.print(f"❌ Error: {str(e)}", style="red")
        console.print("💡 Try checking your GitHub token or network connection", style="yellow")

@app.command()
def analyze(
    repo_url: str = typer.Argument(..., help="GitHub repository URL or owner/repo format")
):
    """Deep analysis of repository suitability for SWE Challenge V3"""
    
    # Parse repository URL/format
    if 'github.com' in repo_url:
        parts = repo_url.split('/')
        owner, repo = parts[-2], parts[-1]
    elif '/' in repo_url:
        owner, repo = repo_url.split('/')
    else:
        console.print("❌ Invalid format. Use: owner/repo or full GitHub URL", style="red")
        return
    
    console.print(f"🔍 [bold]Analyzing {owner}/{repo} for SWE Challenge V3 suitability...[/bold]", style="green")
    
    try:
        # Use the comprehensive analyzer instead of manual analysis
        with Progress(SpinnerColumn(), TextColumn("Performing deep repository analysis...")) as progress:
            task = progress.add_task("Analyzing...", total=1)
            
            # Initialize the sophisticated analyzer
            analyzer = RepositoryAnalyzer()
            
            # Use the comprehensive analysis method
            analysis = analyzer.analyze_repository_deep(owner, repo)
            
            progress.advance(task)
        
        if not analysis:
            console.print(f"❌ Could not analyze repository {owner}/{repo}", style="red")
            return
        
        # Display comprehensive results
        console.print(f"\n📊 [bold]Repository Analysis: {owner}/{repo}[/bold]")
        
        # Overall score with color coding
        score = analysis['overall_score']
        actual_percentage = (score / 5) * 100  # Correct percentage calculation (0-5 scale to 0-100%)
        
        if score >= 4.0:
            score_color = "green"
            score_emoji = "🎯"
        elif score >= 3.0:
            score_color = "yellow" 
            score_emoji = "⚠️"
        else:
            score_color = "red"
            score_emoji = "❌"
        
        console.print(f"{score_emoji} [bold {score_color}]Overall Suitability Score: {score:.1f}/5.0 ({actual_percentage:.1f}%)[/bold {score_color}]")
        
        # Detailed scoring breakdown
        console.print(f"\n📈 [bold]Detailed Scoring:[/bold]")
        console.print(f"🔥 Activity Score: {analysis['activity_score']:.1f}/5.0 (30% weight)")
        console.print(f"🎯 Opportunity Score: {analysis['opportunity_score']:.1f}/5.0 (35% weight)")
        console.print(f"⚙️ Complexity Score: {analysis['complexity_score']:.1f}/5.0 (20% weight)")
        console.print(f"🔧 Maintainability Score: {analysis['maintainability_score']:.1f}/5.0 (15% weight)")
        
        # Show recommendation
        console.print(f"\n💡 [bold]Recommendation:[/bold]")
        console.print(f"   {analysis['recommendation']}")
        
        # Show specific contribution opportunities
        if analysis['opportunities']:
            console.print(f"\n🎯 [bold]Contribution Opportunities Found ({len(analysis['opportunities'])}):[/bold]")
            for i, opp in enumerate(analysis['opportunities'], 1):
                console.print(f"  {i}. {opp['type']}")
                console.print(f"     📝 {opp['title']}")
                console.print(f"     🔗 {opp['url']}")
                console.print()
        else:
            console.print(f"\n🔍 [bold]No specific contribution opportunities found[/bold]")
            console.print("💡 Try checking the repository directly for unlabeled issues")
        
        # Show positive factors
        if analysis['reasons']:
            console.print(f"\n✅ [bold]Positive Factors:[/bold]")
            for reason in analysis['reasons']:
                console.print(f"   {reason}")
        
        # Show warnings if any
        if analysis['warnings']:
            console.print(f"\n⚠️ [bold]Potential Issues:[/bold]")
            for warning in analysis['warnings']:
                console.print(f"   {warning}")
        
        # Actionable next steps based on score
        console.print(f"\n🚀 [bold]Next Steps:[/bold]")
        if score >= 4.0:
            console.print("   • Start with the contribution opportunities listed above")
            console.print("   • Read the repository's CONTRIBUTING.md file")
            console.print("   • Set up the development environment")
            console.print("   • Look for 'good first issue' labels")
        elif score >= 3.0:
            console.print("   • Carefully review the potential issues listed")
            console.print("   • Consider if you're comfortable with the complexity")
            console.print("   • Look for well-defined, smaller issues")
            console.print("   • Check if the repository has clear documentation")
        else:
            console.print("   • Consider searching for a different repository")
            console.print(f"   • Try: python -m github_repo_selector search --min-stars 1000 --max-stars 5000")
            console.print("   • Look for repositories with recent activity")
            console.print("   • Focus on repositories with good first issue labels")
        
        # Save to database if analysis was successful
        if analysis['overall_score'] > 0:
            try:
                db = RepositoryDatabase()
                repo_data = {
                    'repo_name': f"{owner}/{repo}",
                    'stars': analysis.get('stars', 0),
                    'license': analysis.get('license', ''),
                    'py_files_estimate': 0,
                    'python_percentage': '',
                    'url': f"https://github.com/{owner}/{repo}",
                    'description': analysis.get('description', ''),
                    'passes_criteria': analysis['is_suitable'],
                    'analysis_score': analysis['overall_score']
                }
                db.add_repositories([repo_data], {'type': 'manual_analysis'}, 0)
                console.print(f"\n💾 Analysis saved to your database", style="dim")
            except Exception as e:
                console.print(f"\n⚠️ Could not save to database: {e}", style="dim yellow")
        
    except requests.exceptions.RequestException as e:
        console.print(f"❌ Network error: {e}", style="red")
        console.print("💡 Check your internet connection and GitHub token", style="yellow")
    except Exception as e:
        console.print(f"❌ Error analyzing repository: {e}", style="red")
        console.print("💡 Make sure the repository exists and your GitHub token is valid", style="yellow")

@app.command()
def stats():
    """Show user-specific database statistics and history"""
    db = RepositoryDatabase()
    stats = db.get_statistics()
    
    console.print("📊 [bold]Repository Database Statistics[/bold]", style="green")
    
    table = Table(title=f"Database Overview - User: {stats.get('user_id', 'unknown')}")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="yellow")
    
    table.add_row("Total Repositories Tracked", str(stats['total_repositories']))
    table.add_row("Repositories Passing Criteria", str(stats['passing_repositories']))
    table.add_row("Repositories Shown Recently", str(stats['recent_repositories']))
    table.add_row("Total Searches Performed", str(stats['total_searches']))
    
    console.print(table)
    
    if stats['total_repositories'] > 0:
        console.print(f"\n💡 Use --days-filter to control freshness (default: 7 days)")
        console.print(f"💡 Use --allow-repeats to see repos you've seen before")
        console.print(f"💡 Use --force-refresh to ignore all filtering")
        console.print(f"🔄 Database tracks your personal repository history")

@app.command()
def cleanup(
    days_to_keep: int = typer.Option(90, "--days", help="Days of data to keep"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm cleanup action")
):
    """Clean up old repository data for current user"""
    if not confirm:
        console.print("⚠️ This will delete old repository data. Use --confirm to proceed.", style="yellow")
        return
    
    db = RepositoryDatabase()
    deleted = db.cleanup_old_data(days_to_keep) if hasattr(db, 'cleanup_old_data') else 0
    console.print(f"🗑️ Database cleanup complete. Removed {deleted} old entries.", style="green")

@app.command()
def reset(
    confirm: bool = typer.Option(False, "--confirm", help="Confirm database reset")
):
    """Reset the user-specific repository database"""
    if not confirm:
        console.print("⚠️ This will delete ALL your tracked repositories. Use --confirm to proceed.", style="yellow")
        return
    
    db = RepositoryDatabase()
    
    # If user-specific reset method exists, use it
    if hasattr(db, 'reset_user_data'):
        db.reset_user_data()
    else:
        # Fallback: recreate database
        import os
        if os.path.exists(db.db_path):
            os.remove(db.db_path)
        db.init_database()
    
    console.print("✅ Database reset complete. All repository history cleared.", style="green")

@app.command()
def info():
    """Show information about the tool and SWE Challenge V3 criteria"""
    console.print("🚀 [bold]GitHub Repository Selector for SWE Challenge V3[/bold]", style="green")
    
    console.print("\n📋 [bold]Selection Criteria:[/bold]")
    console.print(f"   • Stars: {MIN_STARS:,} - {MAX_STARS:,}")
    console.print(f"   • Python files: {MIN_PY_FILES}+ (estimated)")
    console.print(f"   • Max Python files: {MAX_PY_FILES} (for manageability)")
    console.print(f"   • License: Must be in approved list ({len(ALLOWED_LICENSES)} allowed)")
    console.print(f"   • Python percentage: 70%+ of codebase")
    
    console.print("\n💡 [bold]Usage Examples:[/bold]")
    console.print("   python main.py search --limit 20")
    console.print("   python main.py search --days-filter 14  # Show repos not seen in 14 days")
    console.print("   python main.py search --allow-repeats  # Include repos you've seen before")
    console.print("   python main.py search --force-refresh  # Show all repos, ignore filtering")
    console.print("   python main.py analyze owner/repo  # Analyze specific repository")
    console.print("   python main.py stats  # View your database statistics")
    console.print("   python main.py cleanup --confirm  # Clean old data")
    console.print("   python main.py reset --confirm  # Reset your database")
    
    console.print("\n🎯 [bold]User-Specific Database Features:[/bold]")
    console.print("   • Tracks repositories YOU'VE seen (per-user)")
    console.print("   • Automatically filters out your recent repos")
    console.print("   • Uses smart search strategies for fresh results")
    console.print("   • Maintains your personal search history")
    console.print("   • Ensures you always get fresh candidates!")
    
    console.print("\n🔄 [bold]Fresh Results System:[/bold]")
    console.print("   • Multiple search strategies to find new repos")
    console.print("   • Pagination support for deeper GitHub searches")
    console.print("   • User-specific filtering (your history doesn't affect others)")
    console.print("   • Guaranteed fresh results with fallback mechanisms")

@app.command()
def export_db(
    format: str = typer.Option("json", "--format", help="Export format: json, csv, yaml, markdown"),
    output_file: str = typer.Option(None, "--output", help="Output filename (auto-generated if not specified)"),
    show_summary: bool = typer.Option(True, "--summary/--no-summary", help="Show summary table")
):
    """Export database to human-readable format"""
    db = RepositoryDatabase()
    exporter = DatabaseExporter(db.db_path)
    
    # Get current user ID
    user_id = db.user_id if hasattr(db, 'user_id') else 'default_user'
    
    # Get repositories
    repositories = exporter.get_user_repositories(user_id)
    
    if not repositories:
        console.print(f"❌ No repositories found for user: {user_id}", style="red")
        return
    
    # Show summary if requested
    if show_summary:
        exporter.display_summary(repositories)
        stats = exporter.get_statistics(repositories)
        
        console.print(f"\n📊 [bold]Database Statistics:[/bold]")
        console.print(f"   • Total: {stats['total_repositories']} repositories")
        console.print(f"   • Passing criteria: {stats['passing_criteria']}")
        console.print(f"   • Average stars: {stats['average_stars']:,.0f}")
        console.print(f"   • Most recent: {stats['most_recent']}")
    
    # Generate filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"repositories_{user_id}_{timestamp}.{format}"
    
    # Export based on format
    success = False
    if format.lower() == "json":
        success = exporter.export_to_json(repositories, output_file)
    elif format.lower() == "csv":
        success = exporter.export_to_csv(repositories, output_file)
    elif format.lower() == "yaml":
        success = exporter.export_to_yaml(repositories, output_file)
    elif format.lower() == "markdown":
        success = exporter.export_to_markdown(repositories, output_file)
    else:
        console.print(f"❌ Unsupported format: {format}", style="red")
        console.print("💡 Supported formats: json, csv, yaml, markdown", style="blue")
        return
    
    if success:
        console.print(f"🎉 Database exported successfully!", style="green")
        console.print(f"📁 File: {output_file}", style="blue")

if __name__ == "__main__":
    app()

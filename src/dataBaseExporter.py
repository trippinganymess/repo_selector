import sqlite3
import json
import csv
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table

console = Console()

class DatabaseExporter:
    """Export repository database to human-readable formats"""
    
    def __init__(self, db_path: str = "repositories.db"):
        self.db_path = db_path
    
    def get_user_repositories(self, user_id: str) -> List[Dict]:
        """Get all repositories for a specific user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get user-specific table name
                table_name = f"user_repositories_{user_id}"
                
                # Check if table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table_name,))
                
                if not cursor.fetchone():
                    return []
                
                # Get all repositories with detailed info
                cursor.execute(f"""
                    SELECT repo_name, stars, license, py_files_estimate, python_percentage, 
                           url, description, first_shown, last_shown, show_count, passes_criteria,
                           search_criteria
                    FROM {table_name}
                    ORDER BY last_shown DESC
                """)
                
                rows = cursor.fetchall()
                columns = ['repo_name', 'stars', 'license', 'py_files_estimate', 'python_percentage', 
                          'url', 'description', 'first_shown', 'last_shown', 'show_count', 
                          'passes_criteria', 'search_criteria']
                
                # Convert to list of dictionaries
                repositories = []
                for row in rows:
                    repo_dict = dict(zip(columns, row))
                    # Parse search_criteria JSON if it exists
                    if repo_dict['search_criteria']:
                        try:
                            repo_dict['search_criteria'] = json.loads(repo_dict['search_criteria'])
                        except:
                            pass
                    repositories.append(repo_dict)
                
                return repositories
                
        except Exception as e:
            console.print(f"❌ Error reading database: {e}", style="red")
            return []
    
    def export_to_json(self, repositories: List[Dict], filename: str):
        """Export repositories to JSON format"""
        try:
            export_data = {
                "export_info": {
                    "exported_at": datetime.now().isoformat(),
                    "total_repositories": len(repositories),
                    "format": "json"
                },
                "repositories": repositories
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            console.print(f"✅ Exported {len(repositories)} repositories to {filename}", style="green")
            return True
            
        except Exception as e:
            console.print(f"❌ Error exporting to JSON: {e}", style="red")
            return False
    
    def export_to_csv(self, repositories: List[Dict], filename: str):
        """Export repositories to CSV format"""
        try:
            if not repositories:
                console.print("❌ No repositories to export", style="red")
                return False
            
            # Flatten search_criteria for CSV
            flattened_repos = []
            for repo in repositories:
                flat_repo = repo.copy()
                if isinstance(repo.get('search_criteria'), dict):
                    # Add search criteria as separate columns
                    search_criteria = repo['search_criteria']
                    flat_repo['search_min_stars'] = search_criteria.get('min_stars', '')
                    flat_repo['search_max_stars'] = search_criteria.get('max_stars', '')
                    flat_repo['search_limit'] = search_criteria.get('limit', '')
                flat_repo.pop('search_criteria', None)
                flattened_repos.append(flat_repo)
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if flattened_repos:
                    fieldnames = flattened_repos[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(flattened_repos)
            
            console.print(f"✅ Exported {len(repositories)} repositories to {filename}", style="green")
            return True
            
        except Exception as e:
            console.print(f"❌ Error exporting to CSV: {e}", style="red")
            return False
    
    def export_to_yaml(self, repositories: List[Dict], filename: str):
        """Export repositories to YAML format"""
        try:
            export_data = {
                "export_info": {
                    "exported_at": datetime.now().isoformat(),
                    "total_repositories": len(repositories),
                    "format": "yaml"
                },
                "repositories": repositories
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            console.print(f"✅ Exported {len(repositories)} repositories to {filename}", style="green")
            return True
            
        except Exception as e:
            console.print(f"❌ Error exporting to YAML: {e}", style="red")
            return False
    
    def export_to_markdown(self, repositories: List[Dict], filename: str):
        """Export repositories to Markdown format"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# Repository Database Export\n\n")
                f.write(f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Total Repositories:** {len(repositories)}\n\n")
                
                for i, repo in enumerate(repositories, 1):
                    f.write(f"## {i}. {repo['repo_name']}\n\n")
                    f.write(f"- **⭐ Stars:** {repo['stars']:,}\n")
                    f.write(f"- **📜 License:** {repo['license']}\n")
                    f.write(f"- **🐍 Python %:** {repo['python_percentage']}\n")
                    f.write(f"- **📁 Est. Python Files:** {repo['py_files_estimate']}\n")
                    f.write(f"- **👀 Times Shown:** {repo['show_count']}\n")
                    f.write(f"- **✅ Passes Criteria:** {'Yes' if repo['passes_criteria'] else 'No'}\n")
                    f.write(f"- **🔗 URL:** [{repo['repo_name']}]({repo['url']})\n")
                    f.write(f"- **📝 Description:** {repo['description']}\n")
                    f.write(f"- **📅 First Seen:** {repo['first_shown'][:10]}\n")
                    f.write(f"- **📅 Last Seen:** {repo['last_shown'][:10]}\n\n")
                    f.write("---\n\n")
            
            console.print(f"✅ Exported {len(repositories)} repositories to {filename}", style="green")
            return True
            
        except Exception as e:
            console.print(f"❌ Error exporting to Markdown: {e}", style="red")
            return False
    
    def display_summary(self, repositories: List[Dict]):
        """Display a summary table of repositories"""
        if not repositories:
            console.print("❌ No repositories found", style="red")
            return
        
        table = Table(title=f"Repository Database Summary ({len(repositories)} repos)")
        table.add_column("Repository", style="cyan", width=30)
        table.add_column("Stars", justify="right", style="yellow")
        table.add_column("License", style="green")
        table.add_column("Python %", justify="right", style="blue")
        table.add_column("Last Seen", style="magenta")
        table.add_column("Times Shown", justify="right", style="red")
        
        for repo in repositories[:20]:  # Show top 20
            table.add_row(
                repo['repo_name'],
                f"{repo['stars']:,}",
                repo['license'][:15] + "..." if len(repo['license']) > 15 else repo['license'],
                repo['python_percentage'],
                repo['last_shown'][:10],
                str(repo['show_count'])
            )
        
        console.print(table)
        
        if len(repositories) > 20:
            console.print(f"\n... and {len(repositories) - 20} more repositories")
    
    def get_statistics(self, repositories: List[Dict]) -> Dict:
        """Get statistics about the repositories"""
        if not repositories:
            return {}
        
        total = len(repositories)
        passing = sum(1 for r in repositories if r['passes_criteria'])
        
        # License distribution
        licenses = {}
        for repo in repositories:
            license_name = repo['license']
            licenses[license_name] = licenses.get(license_name, 0) + 1
        
        # Star distribution
        stars = [repo['stars'] for repo in repositories]
        avg_stars = sum(stars) / len(stars) if stars else 0
        
        return {
            'total_repositories': total,
            'passing_criteria': passing,
            'average_stars': avg_stars,
            'license_distribution': dict(sorted(licenses.items(), key=lambda x: x[1], reverse=True)),
            'most_recent': repositories[0]['last_shown'][:10] if repositories else 'None'
        }

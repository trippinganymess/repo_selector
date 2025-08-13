import sqlite3
import json
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from rich.console import Console

console = Console()

class RepositoryDatabase:
    """User-specific SQLite database for tracking shown repositories"""
    
    def __init__(self, db_path: str = "repositories.db", user_id: str = None):
        self.db_path = db_path
        # Create user-specific identifier (use system username if not provided)
        self.user_id = user_id or os.getenv('USER') or os.getenv('USERNAME') or 'default_user'
        self.init_database()
    
    def init_database(self):
        """Initialize user-specific database tables"""
        with sqlite3.connect(self.db_path) as conn:
            # User-specific repositories table
            conn.execute(f"""
            CREATE TABLE IF NOT EXISTS user_repositories_{self.user_id} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_name TEXT UNIQUE NOT NULL,
                stars INTEGER,
                license TEXT,
                py_files_estimate INTEGER,
                python_percentage TEXT,
                url TEXT,
                description TEXT,
                first_shown TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_shown TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                show_count INTEGER DEFAULT 1,
                search_criteria TEXT,
                passes_criteria BOOLEAN,
                analysis_score REAL  -- FIXED: Added missing analysis_score column
            )
            """)
            
            # User-specific search history
            conn.execute(f"""
            CREATE TABLE IF NOT EXISTS user_search_history_{self.user_id} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                min_stars INTEGER,
                max_stars INTEGER,
                limit_requested INTEGER,
                repos_found INTEGER,
                new_repos_shown INTEGER,
                search_criteria TEXT,
                search_offset INTEGER DEFAULT 0
            )
            """)
            
            # Create indexes for better performance
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_user_repo_name_{self.user_id} ON user_repositories_{self.user_id}(repo_name)")
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_user_last_shown_{self.user_id} ON user_repositories_{self.user_id}(last_shown)")
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_user_analysis_score_{self.user_id} ON user_repositories_{self.user_id}(analysis_score)")
    
    def get_last_search_offset(self, search_criteria: Dict) -> int:
        """Get the offset for pagination to ensure new results"""
        criteria_key = f"{search_criteria['min_stars']}_{search_criteria['max_stars']}"
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(f"""
            SELECT MAX(search_offset) FROM user_search_history_{self.user_id}
            WHERE min_stars = ? AND max_stars = ?
            AND search_timestamp > datetime('now', '-1 day')
            """, (search_criteria['min_stars'], search_criteria['max_stars'])).fetchone()
            
            return (result[0] or 0) if result else 0
    
    def add_repositories(self, repos: List[Dict], search_criteria: Dict, search_offset: int = 0):
        """Add repositories to user-specific database with proper error handling"""
        with sqlite3.connect(self.db_path) as conn:
            for repo in repos:
                try:
                    # Check if repository already exists for this user
                    existing = conn.execute(f"""
                    SELECT id, show_count FROM user_repositories_{self.user_id}
                    WHERE repo_name = ?
                    """, (repo['repo_name'],)).fetchone()
                    
                    if existing:
                        # Update existing repository
                        conn.execute(f"""
                        UPDATE user_repositories_{self.user_id}
                        SET last_shown = CURRENT_TIMESTAMP,
                            show_count = show_count + 1,
                            stars = ?,
                            license = ?,
                            py_files_estimate = ?,
                            python_percentage = ?,
                            description = ?,
                            analysis_score = ?
                        WHERE repo_name = ?
                        """, (
                            repo.get('stars', 0),
                            repo.get('license', ''),
                            repo.get('py_files_estimate', 0),
                            repo.get('python_percentage', ''),
                            repo.get('description', ''),
                            repo.get('analysis_score', None),  # Handle the new field
                            repo['repo_name']
                        ))
                    else:
                        # Insert new repository for this user
                        conn.execute(f"""
                        INSERT INTO user_repositories_{self.user_id}
                        (repo_name, stars, license, py_files_estimate, python_percentage,
                         url, description, search_criteria, passes_criteria, analysis_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            repo['repo_name'],
                            repo.get('stars', 0),
                            repo.get('license', ''),
                            repo.get('py_files_estimate', 0),
                            repo.get('python_percentage', ''),
                            repo.get('url', ''),
                            repo.get('description', ''),
                            json.dumps(search_criteria),
                            repo.get('passes_criteria', False),
                            repo.get('analysis_score', None)  # Handle the new field
                        ))
                except sqlite3.Error as e:
                    console.print(f"⚠️ Database error for {repo.get('repo_name', 'unknown')}: {e}", style="dim red")
                    continue
            
            # Log this search with offset
            try:
                conn.execute(f"""
                INSERT INTO user_search_history_{self.user_id}
                (min_stars, max_stars, limit_requested, repos_found, new_repos_shown, search_criteria, search_offset)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    search_criteria.get('min_stars', 0),
                    search_criteria.get('max_stars', 0),
                    search_criteria.get('limit', 0),
                    len(repos),
                    len(repos),  # All are new in this context
                    json.dumps(search_criteria),
                    search_offset
                ))
            except sqlite3.Error as e:
                console.print(f"⚠️ Could not log search history: {e}", style="dim red")
    
    def get_shown_repositories(self, days_back: int = 30) -> List[str]:
        """Get list of repository names shown to this user in the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                results = conn.execute(f"""
                SELECT repo_name FROM user_repositories_{self.user_id}
                WHERE last_shown > ?
                ORDER BY last_shown DESC
                """, (cutoff_date.isoformat(),)).fetchall()
                
                return [row[0] for row in results]
        except sqlite3.Error as e:
            console.print(f"⚠️ Database error getting shown repos: {e}", style="dim red")
            return []
    
    def filter_new_repositories(self, repos: List[Dict], days_back: int = 7) -> List[Dict]:
        """Filter out repositories that have been shown to this user recently"""
        shown_repos = set(self.get_shown_repositories(days_back))
        new_repos = [repo for repo in repos if repo['repo_name'] not in shown_repos]
        
        filtered_count = len(repos) - len(new_repos)
        if filtered_count > 0:
            console.print(f"🔄 Filtered out {filtered_count} repos you've seen before (last {days_back} days)")
        
        return new_repos
    
    def get_statistics(self) -> Dict:
        """Get user-specific database statistics with error handling"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                total_repos = conn.execute(f"SELECT COUNT(*) FROM user_repositories_{self.user_id}").fetchone()[0]
                passing_repos = conn.execute(f"SELECT COUNT(*) FROM user_repositories_{self.user_id} WHERE passes_criteria = 1").fetchone()[0]
                recent_repos = conn.execute(f"""
                SELECT COUNT(*) FROM user_repositories_{self.user_id}
                WHERE last_shown > datetime('now', '-7 days')
                """).fetchone()[0]
                total_searches = conn.execute(f"SELECT COUNT(*) FROM user_search_history_{self.user_id}").fetchone()[0]
                
                # Get average analysis score for repositories that have been analyzed
                avg_score_result = conn.execute(f"""
                SELECT AVG(analysis_score) FROM user_repositories_{self.user_id}
                WHERE analysis_score IS NOT NULL
                """).fetchone()
                avg_analysis_score = avg_score_result[0] if avg_score_result and avg_score_result[0] else 0
                
                return {
                    'user_id': self.user_id,
                    'total_repositories': total_repos,
                    'passing_repositories': passing_repos,
                    'recent_repositories': recent_repos,
                    'total_searches': total_searches,
                    'average_analysis_score': round(avg_analysis_score, 2) if avg_analysis_score else 0
                }
        except sqlite3.Error as e:
            console.print(f"⚠️ Database error getting statistics: {e}", style="dim red")
            return {
                'user_id': self.user_id,
                'total_repositories': 0,
                'passing_repositories': 0,
                'recent_repositories': 0,
                'total_searches': 0,
                'average_analysis_score': 0
            }
    
    def get_top_analyzed_repositories(self, limit: int = 10) -> List[Dict]:
        """Get top repositories by analysis score"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                SELECT repo_name, stars, license, analysis_score, url, description, last_shown
                FROM user_repositories_{self.user_id}
                WHERE analysis_score IS NOT NULL
                ORDER BY analysis_score DESC, stars DESC
                LIMIT ?
                """, (limit,))
                
                columns = ['repo_name', 'stars', 'license', 'analysis_score', 'url', 'description', 'last_shown']
                results = []
                
                for row in cursor.fetchall():
                    repo_dict = dict(zip(columns, row))
                    results.append(repo_dict)
                
                return results
        except sqlite3.Error as e:
            console.print(f"⚠️ Database error getting top analyzed repos: {e}", style="dim red")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """Clean up old repository data beyond specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Clean old repositories (but keep analyzed ones)
                repo_result = conn.execute(f"""
                DELETE FROM user_repositories_{self.user_id}
                WHERE last_shown < ? AND analysis_score IS NULL
                """, (cutoff_date.isoformat(),))
                
                # Clean old search history
                search_result = conn.execute(f"""
                DELETE FROM user_search_history_{self.user_id}
                WHERE search_timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                total_deleted = repo_result.rowcount + search_result.rowcount
                conn.commit()
                return total_deleted
        except sqlite3.Error as e:
            console.print(f"⚠️ Database error during cleanup: {e}", style="dim red")
            return 0
    
    def reset_user_data(self):
        """Reset all data for the current user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f"DROP TABLE IF EXISTS user_repositories_{self.user_id}")
                conn.execute(f"DROP TABLE IF EXISTS user_search_history_{self.user_id}")
                conn.commit()
                
            # Reinitialize the database
            self.init_database()
            console.print(f"✅ Reset database for user: {self.user_id}", style="green")
        except sqlite3.Error as e:
            console.print(f"⚠️ Database error during reset: {e}", style="red")
    
    def backup_database(self, backup_path: str = None) -> str:
        """Create a backup of the user's database"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_{self.user_id}_{timestamp}.db"
        
        try:
            # Simple file copy backup
            import shutil
            shutil.copy2(self.db_path, backup_path)
            console.print(f"✅ Database backed up to: {backup_path}", style="green")
            return backup_path
        except Exception as e:
            console.print(f"⚠️ Backup failed: {e}", style="red")
            return ""
    
    def get_repository_by_name(self, repo_name: str) -> Optional[Dict]:
        """Get specific repository details by name"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                SELECT repo_name, stars, license, py_files_estimate, python_percentage,
                       url, description, first_shown, last_shown, show_count, 
                       passes_criteria, analysis_score, search_criteria
                FROM user_repositories_{self.user_id}
                WHERE repo_name = ?
                """, (repo_name,))
                
                row = cursor.fetchone()
                if row:
                    columns = ['repo_name', 'stars', 'license', 'py_files_estimate', 'python_percentage',
                              'url', 'description', 'first_shown', 'last_shown', 'show_count',
                              'passes_criteria', 'analysis_score', 'search_criteria']
                    
                    repo_dict = dict(zip(columns, row))
                    
                    # Parse search_criteria if it exists
                    if repo_dict['search_criteria']:
                        try:
                            repo_dict['search_criteria'] = json.loads(repo_dict['search_criteria'])
                        except json.JSONDecodeError:
                            repo_dict['search_criteria'] = {}
                    
                    return repo_dict
                return None
        except sqlite3.Error as e:
            console.print(f"⚠️ Database error getting repository {repo_name}: {e}", style="dim red")
            return None
    
    def get_repositories_with_analysis(self) -> List[Dict]:
        """Get all repositories that have been analyzed (have analysis_score)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                SELECT repo_name, stars, license, analysis_score, url, description, 
                       last_shown, passes_criteria
                FROM user_repositories_{self.user_id}
                WHERE analysis_score IS NOT NULL
                ORDER BY analysis_score DESC, last_shown DESC
                """)
                
                columns = ['repo_name', 'stars', 'license', 'analysis_score', 'url', 
                          'description', 'last_shown', 'passes_criteria']
                results = []
                
                for row in cursor.fetchall():
                    repo_dict = dict(zip(columns, row))
                    results.append(repo_dict)
                
                return results
        except sqlite3.Error as e:
            console.print(f"⚠️ Database error getting analyzed repositories: {e}", style="dim red")
            return []
    
    def update_analysis_score(self, repo_name: str, analysis_score: float, passes_criteria: bool = None):
        """Update analysis score for a specific repository"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if passes_criteria is not None:
                    conn.execute(f"""
                    UPDATE user_repositories_{self.user_id}
                    SET analysis_score = ?, passes_criteria = ?, last_shown = CURRENT_TIMESTAMP
                    WHERE repo_name = ?
                    """, (analysis_score, passes_criteria, repo_name))
                else:
                    conn.execute(f"""
                    UPDATE user_repositories_{self.user_id}
                    SET analysis_score = ?, last_shown = CURRENT_TIMESTAMP
                    WHERE repo_name = ?
                    """, (analysis_score, repo_name))
                
                if conn.total_changes > 0:
                    console.print(f"✅ Updated analysis score for {repo_name}: {analysis_score:.1f}/5.0", style="dim green")
                    return True
                else:
                    console.print(f"⚠️ Repository {repo_name} not found in database", style="dim yellow")
                    return False
                    
        except sqlite3.Error as e:
            console.print(f"⚠️ Database error updating analysis score: {e}", style="dim red")
            return False

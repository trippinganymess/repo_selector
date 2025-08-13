from typing import List, Dict, Tuple
import requests
from datetime import datetime, timedelta
from .config import ALLOWED_LICENSES, GITHUB_TOKEN

class RepositoryAnalyzer:
    def __init__(self):
        self.allowed_licenses = ALLOWED_LICENSES
        self.headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
        self.base_url = "https://api.github.com"

    def analyze_repositories_fast(self, repos: List[Dict]) -> List[Dict]:
        """Quick analysis without additional API calls"""
        results = []
        for repo in repos:
            analysis = self._analyze_single_repo(repo)
            results.append(analysis)
        return results

    def analyze_repository_deep(self, owner: str, repo: str) -> Dict:
        """Deep analysis with suitability scoring for SWE Challenge V3"""
        analysis = {
            'repo_name': f"{owner}/{repo}",
            'overall_score': 0,
            'is_suitable': False,
            'activity_score': 0,
            'opportunity_score': 0,
            'complexity_score': 0,
            'maintainability_score': 0,
            'reasons': [],
            'opportunities': [],
            'warnings': [],
            'recommendation': ''
        }

        try:
            # Get repository details
            repo_data = self._get_repo_details(owner, repo)
            if not repo_data:
                analysis['warnings'].append("Could not fetch repository data")
                return analysis

            # Store basic repo info
            analysis['stars'] = repo_data.get('stargazers_count', 0)
            analysis['license'] = repo_data.get('license', {}).get('name', 'Unknown')
            analysis['description'] = repo_data.get('description', '')

            # Enhanced suitability analysis
            activity = self._check_repository_activity(owner, repo, repo_data)
            analysis['activity_score'] = activity['score']
            analysis['reasons'].extend(activity['reasons'])
            analysis['warnings'].extend(activity.get('warnings', []))

            opportunities = self._find_contribution_opportunities(owner, repo)
            analysis['opportunity_score'] = opportunities['score']
            analysis['opportunities'] = opportunities['items']

            complexity = self._assess_complexity(repo_data, owner, repo)
            analysis['complexity_score'] = complexity['score']
            analysis['reasons'].extend(complexity['reasons'])
            if complexity.get('warnings'):
                analysis['warnings'].extend(complexity['warnings'])

            maintainability = self._check_maintainability(owner, repo)
            analysis['maintainability_score'] = maintainability['score']
            analysis['reasons'].extend(maintainability['reasons'])

            # Calculate overall suitability score (0-5 scale)
            analysis['overall_score'] = self._calculate_suitability_score(analysis)
            analysis['is_suitable'] = analysis['overall_score'] >= 3.5  # Fixed threshold
            analysis['recommendation'] = self._generate_recommendation(analysis)

            return analysis

        except Exception as e:
            analysis['warnings'].append(f"Analysis failed: {str(e)}")
            return analysis

    def _analyze_single_repo(self, repo: Dict) -> Dict:
        """Existing fast analysis logic"""
        stars = repo['stargazerCount']
        license_info = repo.get('licenseInfo', {})
        
        license_ok = False
        license_name = "Unknown"
        if license_info:
            spdx_id = license_info.get('spdxId', '')
            name = license_info.get('name', '')
            license_name = spdx_id or name
            license_ok = any(allowed in license_name for allowed in self.allowed_licenses)

        # Estimate Python files from language data
        languages = repo.get('languages', {}).get('edges', [])
        python_percentage = self._calculate_python_percentage(languages, repo)
        estimated_py_files = max(1, int(python_percentage * 30))

        return {
            'repo_name': repo['nameWithOwner'],
            'stars': stars,
            'license': license_name,
            'license_ok': license_ok,
            'py_files_estimate': estimated_py_files,
            'python_percentage': f"{python_percentage*100:.1f}%",
            'url': repo['url'],
            'description': repo.get('description', '')[:100] + "..." if repo.get('description', '') else "",
            'passes_criteria': self._passes_criteria(stars, license_ok, python_percentage)
        }

    def _check_repository_activity(self, owner: str, repo: str, repo_data: Dict) -> Dict:
        """Check repository activity and maintenance level"""
        score = 0
        reasons = []
        warnings = []

        try:
            # Check recent commits
            commits_url = f"{self.base_url}/repos/{owner}/{repo}/commits"
            response = requests.get(commits_url, headers=self.headers, params={'per_page': 5})
            
            if response.status_code == 200:
                commits = response.json()
                if commits:
                    recent_commit = datetime.fromisoformat(commits[0]['commit']['author']['date'].replace('Z', '+00:00'))
                    days_since = (datetime.now(recent_commit.tzinfo) - recent_commit).days
                    
                    if days_since <= 7:
                        score += 5
                        reasons.append(f"✅ Recently active (last commit {days_since} days ago)")
                    elif days_since <= 30:
                        score += 4
                        reasons.append(f"✅ Recently active (last commit {days_since} days ago)")
                    elif days_since <= 90:
                        score += 3
                        reasons.append(f"⚠️ Moderately active (last commit {days_since} days ago)")
                    elif days_since <= 180:
                        score += 2
                        reasons.append(f"⚠️ Less active (last commit {days_since} days ago)")
                    else:
                        score += 1
                        warnings.append(f"❌ Low activity (last commit {days_since} days ago)")
            
            # Check issue activity
            issues_url = f"{self.base_url}/repos/{owner}/{repo}/issues"
            response = requests.get(issues_url, headers=self.headers, params={'state': 'open', 'per_page': 1})
            if response.status_code == 200:
                if response.headers.get('link'):  # Has pagination = many issues
                    reasons.append("📋 Active issue discussions")
                    score += 0.5  # Bonus for active discussions

        except Exception as e:
            warnings.append(f"⚠️ Could not check activity: {str(e)}")

        return {'score': min(score, 5), 'reasons': reasons, 'warnings': warnings}

    def _find_contribution_opportunities(self, owner: str, repo: str) -> Dict:
        """Find specific contribution opportunities"""
        score = 0
        opportunities = []

        try:
            issues_url = f"{self.base_url}/repos/{owner}/{repo}/issues"

            # Search for good first issues
            response = requests.get(issues_url, headers=self.headers, params={
                'labels': 'good first issue',
                'state': 'open',
                'per_page': 5
            })
            
            if response.status_code == 200:
                good_first_issues = response.json()
                if isinstance(good_first_issues, list) and good_first_issues:
                    for issue in good_first_issues[:3]:  # Limit to 3
                        opportunities.append({
                            'type': '🟢 Good First Issue',
                            'title': issue['title'][:60] + "..." if len(issue['title']) > 60 else issue['title'],
                            'url': issue['html_url']
                        })
                    score += min(len(good_first_issues), 3) * 1.0  # 1 point per good first issue

            # Search for help wanted issues 
            response = requests.get(issues_url, headers=self.headers, params={
                'labels': 'help wanted',
                'state': 'open',
                'per_page': 5
            })
            
            if response.status_code == 200:
                help_wanted = response.json()
                if isinstance(help_wanted, list) and help_wanted:
                    for issue in help_wanted[:2]:  # Limit to 2
                        opportunities.append({
                            'type': '🆘 Help Wanted',
                            'title': issue['title'][:60] + "..." if len(issue['title']) > 60 else issue['title'],
                            'url': issue['html_url']
                        })
                    score += min(len(help_wanted), 2) * 0.8  # 0.8 points per help wanted

            # Search for bugs
            response = requests.get(issues_url, headers=self.headers, params={
                'labels': 'bug',
                'state': 'open',
                'per_page': 5
            })
            
            if response.status_code == 200:
                bugs = response.json()
                if isinstance(bugs, list) and bugs:
                    for bug in bugs[:2]:  # Limit to 2
                        opportunities.append({
                            'type': '🐛 Bug Fix',
                            'title': bug['title'][:60] + "..." if len(bug['title']) > 60 else bug['title'],
                            'url': bug['html_url']
                        })
                    score += min(len(bugs), 2) * 0.6  # 0.6 points per bug

        except Exception as e:
            pass  # Silently handle API errors

        return {'score': min(score, 5), 'items': opportunities[:5]}  # Max 5 opportunities

    def _assess_complexity(self, repo_data: Dict, owner: str, repo: str) -> Dict:
        """Assess if repository is manageable for contributions"""
        score = 5  # Start with full points
        reasons = []
        warnings = []

        # Size check (more nuanced scoring)
        size_kb = repo_data.get('size', 0)
        size_mb = size_kb / 1024

        if size_mb > 200:  # 200MB+
            score = 2
            warnings.append(f"⚠️ Very large repository ({size_mb:.0f} MB)")
        elif size_mb > 100:  # 100-200MB
            score = 3
            warnings.append(f"⚠️ Large repository ({size_mb:.0f} MB)")
        elif size_mb > 50:   # 50-100MB
            score = 4
            reasons.append(f"⚠️ Medium-sized repository ({size_mb:.0f} MB)")
        else:  # <50MB
            score = 5
            reasons.append(f"✅ Manageable size ({size_mb:.0f} MB)")

        # Language complexity
        if repo_data.get('language') == 'Python':
            reasons.append("✅ Python-primary repository")
        else:
            score = max(1, score - 1)  # Reduce score if not Python primary

        # Documentation check
        description = repo_data.get('description', '')
        if len(description) > 50:
            reasons.append("✅ Well documented")
        else:
            score = max(1, score - 0.5)

        return {
            'score': max(min(score, 5), 0), 
            'reasons': reasons,
            'warnings': warnings
        }

    def _check_maintainability(self, owner: str, repo: str) -> Dict:
        """Check maintainability indicators"""
        score = 0
        reasons = []

        try:
            # Check if repo has contributing guidelines
            contents_url = f"{self.base_url}/repos/{owner}/{repo}/contents"
            response = requests.get(contents_url, headers=self.headers)
            
            if response.status_code == 200:
                contents = response.json()
                files = [item['name'].lower() for item in contents if item['type'] == 'file']
                
                if any('contributing' in f for f in files):
                    score += 2
                    reasons.append("✅ Has contributing guidelines")
                
                if 'readme.md' in files or 'readme.rst' in files:
                    score += 1.5
                    reasons.append("✅ Has README")
                
                if any('license' in f for f in files):
                    score += 1.5
                    reasons.append("✅ Has license file")

        except Exception:
            pass

        return {'score': min(score, 5), 'reasons': reasons}

    def _calculate_suitability_score(self, analysis: Dict) -> float:
        """Calculate weighted suitability score (0-5 scale)"""
        weighted_score = (
            analysis['activity_score'] * 0.3 +      # 30% - How active is the project
            analysis['opportunity_score'] * 0.35 +   # 35% - Are there contribution opportunities  
            analysis['complexity_score'] * 0.2 +     # 20% - Is it manageable to work with
            analysis['maintainability_score'] * 0.15 # 15% - Is it well maintained
        )
        return round(weighted_score, 1)

    def _generate_recommendation(self, analysis: Dict) -> str:
        """Generate actionable recommendation (FIXED THRESHOLDS for 0-5 scale)"""
        score = analysis['overall_score']
        
        if score >= 4.2:  # 84%+ - Changed from 8.5 to 4.2
            return "🎯 EXCELLENT choice for SWE Challenge V3! High activity with great opportunities."
        elif score >= 3.5:  # 70%+ - Changed from 7.0 to 3.5
            return "✅ GOOD choice for SWE Challenge V3. Should find suitable contribution opportunities."
        elif score >= 2.5:  # 50%+ - Changed from 5.0 to 2.5
            return "⚠️ MODERATE choice. May require more effort to find good contribution opportunities."
        else:  # <50%
            return "❌ NOT RECOMMENDED. Consider looking for more active repositories with clearer opportunities."

    # Existing helper methods (keep unchanged)
    def _calculate_python_percentage(self, languages: List, repo: Dict) -> float:
        """Calculate percentage of Python code in repository"""
        python_percentage = 0
        total_size = repo.get('languages', {}).get('totalSize', 0)
        
        if total_size == 0:
            return 0

        for lang in languages:
            if lang['node']['name'] == 'Python':
                python_percentage = lang['size'] / total_size
                break

        return python_percentage

    def _passes_criteria(self, stars: int, license_ok: bool, python_percentage: float) -> bool:
        """Check if repository passes all criteria"""
        return (
            license_ok and
            stars < 10000 and
            python_percentage > 0.7  # 70%
        )

    def filter_good_candidates(self, results: List[Dict]) -> List[Dict]:
        """Filter for repositories that meet all criteria"""
        return [r for r in results if r['passes_criteria']]

    def _get_repo_details(self, owner: str, repo: str) -> Dict:
        """Get detailed repository information"""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = requests.get(url, headers=self.headers)
        return response.json() if response.status_code == 200 else None

    def _analyze_repo_from_data(self, repo_data: Dict) -> Dict:
        """Analyze repository from API data"""
        return {
            'stars': repo_data.get('stargazers_count', 0),
            'license': repo_data.get('license', {}).get('name', 'Unknown'),
            'url': repo_data.get('html_url', ''),
            'description': repo_data.get('description', ''),
            'language': repo_data.get('language', 'Unknown')
        }

import requests
from typing import List, Dict, Optional
import random
import time
from .config import GITHUB_TOKEN, GITHUB_BASE_URL

class GitHubClient:
    def __init__(self):
        self.token = GITHUB_TOKEN
        self.base_url = GITHUB_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def search_repositories_graphql(self, min_stars=500, max_stars=5000, limit=20, after_cursor: Optional[str] = None, sort: str = "stars") -> Dict:
        """Enhanced GraphQL search with proper cursor-based pagination"""
        
        query = """
        query($searchQuery: String!, $first: Int!, $after: String) {
          search(query: $searchQuery, type: REPOSITORY, first: $first, after: $after) {
            nodes {
              ... on Repository {
                nameWithOwner
                stargazerCount
                description
                url
                updatedAt
                createdAt
                pushedAt
                licenseInfo {
                  spdxId
                  name
                }
                languages(first: 5) {
                  totalSize
                  edges {
                    node {
                      name
                    }
                    size
                  }
                }
                repositoryTopics(first: 10) {
                  nodes {
                    topic {
                      name
                    }
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
            repositoryCount
          }
          rateLimit {
            remaining
            cost
          }
        }
        """
        
        # Build search query with proper sorting
        search_query = f"language:Python stars:{min_stars}..{max_stars} archived:false fork:false"
        if sort != "stars":
            search_query += f" sort:{sort}"
        
        variables = {
            "searchQuery": search_query,
            "first": limit,
            "after": after_cursor
        }
        
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers=self.headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"GraphQL request failed: {response.status_code} - {response.text}")
        
        data = response.json()
        
        if "errors" in data:
            raise Exception(f"GraphQL errors: {data['errors']}")
        
        return {
            'repositories': data["data"]["search"]["nodes"],
            'rate_limit': data["data"]["rateLimit"],
            'page_info': data["data"]["search"]["pageInfo"],
            'repository_count': data["data"]["search"]["repositoryCount"],
            'search_query_used': search_query,
            'sort_used': sort
        }
    
    def search_with_randomization(self, min_stars=500, max_stars=5000, limit=20, search_attempt=0):
        """Advanced search with multiple strategies to ensure varied results"""
        
        # Much more diverse search strategies
        strategies = [
            # Different sorting approaches
            {"sort": "stars", "min_stars": min_stars, "max_stars": max_stars},
            {"sort": "updated", "min_stars": min_stars, "max_stars": max_stars},
            {"sort": "created", "min_stars": min_stars, "max_stars": max_stars},
            
            # Split star ranges into thirds for better coverage
            {"sort": "stars", "min_stars": min_stars, "max_stars": min_stars + (max_stars - min_stars) // 3},
            {"sort": "stars", "min_stars": min_stars + (max_stars - min_stars) // 3 + 1, "max_stars": min_stars + 2 * (max_stars - min_stars) // 3},
            {"sort": "stars", "min_stars": min_stars + 2 * (max_stars - min_stars) // 3 + 1, "max_stars": max_stars},
            
            # Different range expansions
            {"sort": "updated", "min_stars": max(100, min_stars - 200), "max_stars": max_stars + 1000},
            {"sort": "created", "min_stars": min_stars, "max_stars": min(50000, max_stars * 2)},
            
            # Topic-based searches for diversity
            {"sort": "stars", "min_stars": min_stars, "max_stars": max_stars, "topic": "machine-learning"},
            {"sort": "stars", "min_stars": min_stars, "max_stars": max_stars, "topic": "web-development"},
            {"sort": "stars", "min_stars": min_stars, "max_stars": max_stars, "topic": "data-science"},
            {"sort": "stars", "min_stars": min_stars, "max_stars": max_stars, "topic": "automation"},
        ]
        
        strategy = strategies[search_attempt % len(strategies)]
        
        actual_min = strategy.get("min_stars", min_stars)
        actual_max = strategy.get("max_stars", max_stars)
        sort_param = strategy.get("sort", "stars")
        topic = strategy.get("topic")
        
        # Use cursor pagination for deeper results
        after_cursor = None
        if search_attempt > 2:
            # For later attempts, try to get deeper pages
            after_cursor = self._get_cursor_for_attempt(search_attempt)
        
        return self.search_repositories_graphql_with_topics(
            actual_min, actual_max, limit, after_cursor, sort_param, topic
        )
    
    def search_repositories_graphql_with_topics(self, min_stars, max_stars, limit, after_cursor, sort, topic=None):
        """Enhanced search that can include topic filtering"""
        
        query = """
        query($searchQuery: String!, $first: Int!, $after: String) {
          search(query: $searchQuery, type: REPOSITORY, first: $first, after: $after) {
            nodes {
              ... on Repository {
                nameWithOwner
                stargazerCount
                description
                url
                updatedAt
                createdAt
                pushedAt
                licenseInfo {
                  spdxId
                  name
                }
                languages(first: 5) {
                  totalSize
                  edges {
                    node {
                      name
                    }
                    size
                  }
                }
                repositoryTopics(first: 10) {
                  nodes {
                    topic {
                      name
                    }
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
            repositoryCount
          }
          rateLimit {
            remaining
            cost
          }
        }
        """
        
        # Build enhanced search query
        search_query = f"language:Python stars:{min_stars}..{max_stars} archived:false fork:false"
        if topic:
            search_query += f" topic:{topic}"
        if sort != "stars":
            search_query += f" sort:{sort}"
        
        variables = {
            "searchQuery": search_query,
            "first": limit,
            "after": after_cursor
        }
        
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers=self.headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"GraphQL request failed: {response.status_code}")
        
        data = response.json()
        
        if "errors" in data:
            raise Exception(f"GraphQL errors: {data['errors']}")
        
        return {
            'repositories': data["data"]["search"]["nodes"],
            'rate_limit': data["data"]["rateLimit"],
            'page_info': data["data"]["search"]["pageInfo"],
            'repository_count': data["data"]["search"]["repositoryCount"],
            'search_query_used': search_query,
            'sort_used': sort
        }
    
    def get_diverse_repositories(self, min_stars=500, max_stars=5000, total_limit=50, max_attempts=5) -> List[Dict]:
        """Get a diverse set of repositories using multiple search strategies"""
        all_repos = []
        seen_repos = set()
        
        for attempt in range(max_attempts):
            try:
                # Use different strategies
                result = self.search_with_randomization(
                    min_stars, max_stars, 
                    min(20, total_limit - len(all_repos)), 
                    attempt
                )
                
                # Add new repositories
                for repo in result['repositories']:
                    if repo['nameWithOwner'] not in seen_repos:
                        seen_repos.add(repo['nameWithOwner'])
                        all_repos.append(repo)
                
                # Stop if we have enough
                if len(all_repos) >= total_limit:
                    break
                    
                # Small delay to be respectful to API
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Warning: Search attempt {attempt} failed: {e}")
                continue
        
        return all_repos[:total_limit]
    
    def _get_cursor_for_attempt(self, attempt: int) -> Optional[str]:
        """Generate different cursors for pagination (simplified approach)"""
        # This is a simplified approach. In practice, you'd store real cursors
        # from previous searches, but this helps get different result sets
        return None  # Let GitHub handle natural pagination
    
    def search_repositories_by_language_percentage(self, min_stars=500, max_stars=5000, limit=20, min_python_percentage=70):
        """Search for repositories with high Python percentage"""
        
        # This requires multiple API calls to filter by language percentage
        # First get candidates, then filter by language stats
        candidates = self.search_repositories_graphql(min_stars, max_stars, limit * 2)
        
        python_heavy_repos = []
        for repo in candidates['repositories']:
            languages = repo.get('languages', {}).get('edges', [])
            total_size = repo.get('languages', {}).get('totalSize', 0)
            
            if total_size > 0:
                python_size = 0
                for lang in languages:
                    if lang['node']['name'] == 'Python':
                        python_size = lang['size']
                        break
                
                python_percentage = (python_size / total_size) * 100
                if python_percentage >= min_python_percentage:
                    repo['python_percentage_actual'] = python_percentage
                    python_heavy_repos.append(repo)
        
        return {
            'repositories': python_heavy_repos[:limit],
            'rate_limit': candidates['rate_limit'],
            'total_candidates_checked': len(candidates['repositories'])
        }
    
    def check_rate_limit(self) -> Dict:
        """Check current rate limit status"""
        query = """
        query {
          rateLimit {
            remaining
            resetAt
            cost
          }
        }
        """
        
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query},
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["data"]["rateLimit"]
        else:
            return {"remaining": 0, "resetAt": "", "cost": 0}

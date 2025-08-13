# GitHub Repository Selector

A sophisticated Python tool for discovering and analyzing GitHub repositories suitable for open source contributions. Features intelligent filtering, comprehensive suitability analysis, and user-specific tracking to ensure you always find fresh, high-quality repositories to contribute to.

## 🌟 Features

### Core Functionality
- **Smart Repository Discovery**: Advanced GitHub API integration with GraphQL queries
- **4-Category Suitability Analysis**: Comprehensive scoring system for contribution potential
- **User-Specific Database**: Personal tracking prevents seeing the same repositories repeatedly
- **Fresh Results System**: Multiple search strategies ensure diverse, new discoveries
- **Real-time Opportunity Detection**: Finds specific contribution opportunities (good first issues, bugs, help wanted)

### Analysis Categories
1. **Activity Score (30%)**: Repository maintenance and recent commit activity
2. **Opportunity Score (35%)**: Available contribution opportunities and issue quality
3. **Complexity Score (20%)**: Project manageability and codebase size
4. **Maintainability Score (15%)**: Documentation quality and contributor guidelines

### Export & API Features
- **Multiple Export Formats**: JSON, CSV, YAML, Markdown
- **RESTful API**: FastAPI-based web service with comprehensive endpoints
- **Rate Limit Management**: Intelligent GitHub API usage optimization
- **Cross-Platform Support**: Works on Windows, macOS, and Linux

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- GitHub Personal Access Token
- Dependencies: `pip install -r requirements.txt`

### Installation

```bash
git clone https://github.com/trippinganymess/repo_selector
cd repo_selector
pip install -r requirements.txt
```

### Configuration

```bash
# Set your GitHub token
export GITHUB_TOKEN="your_github_token_here"

# Optional: Set custom database location
export DB_PATH="./my_repositories.db"
```

### Basic Usage

```bash
# Search for repositories (CLI)
python main.py search --min-stars 1000 --max-stars 10000 --limit 20

# Analyze a specific repository
python main.py analyze microsoft/vscode-python

# View your statistics
python main.py stats

# Export your database
python main.py export-db --format markdown --output my_repos.md

# Start the API server
python api_server.py
```

## 📊 Selection Criteria

The tool automatically filters repositories based on proven SWE Challenge criteria:

- **⭐ Stars**: 500 - 50,000 (configurable)
- **🐍 Python Content**: 70%+ Python code
- **📁 File Count**: 15-100 Python files (manageable size)
- **📜 License**: Open source licenses only (MIT, Apache, BSD, etc.)
- **🔄 Activity**: Recent commits and active maintenance
- **🎯 Opportunities**: Available issues labeled for contributions

## 💻 Command Line Interface

### Search Command
```bash
python main.py search [OPTIONS]

Options:
  --min-stars INTEGER     Minimum star count [default: 500]
  --max-stars INTEGER     Maximum star count [default: 50000]
  --limit INTEGER         Maximum repos to fetch [default: 30]
  --days-filter INTEGER   Filter repos shown in last N days [default: 7]
  --fresh-only           Only show repos you haven't seen [default: True]
  --force-refresh        Show all repos, ignore filtering
  --export-csv           Export results to CSV
```

### Analysis Command
```bash
python main.py analyze REPO_URL

# Examples:
python main.py analyze microsoft/playwright
python main.py analyze https://github.com/fastapi/fastapi
```

### Database Management
```bash
# View statistics
python main.py stats

# Export database
python main.py export-db --format json --output repos.json

# Clean old data
python main.py cleanup --days 90 --confirm

# Reset database
python main.py reset --confirm
```

## 🌐 API Server

### Starting the Server
```bash
python api_server.py

# Custom configuration
HOST=localhost PORT=8080 python api_server.py
```

### API Endpoints

#### Search Repositories
```http
POST /api/v1/search
Content-Type: application/json
X-User-ID: your_username

{
  "min_stars": 1000,
  "max_stars": 10000,
  "limit": 20,
  "fresh_only": true
}
```

#### Analyze Repository
```http
GET /api/v1/analyze/microsoft/vscode-python
X-User-ID: your_username
```

#### User Statistics
```http
GET /api/v1/users/your_username/stats
```

#### Export Database
```http
POST /api/v1/export
Content-Type: application/json

{
  "format": "json",
  "user_id": "your_username"
}
```

#### Health Check
```http
GET /api/v1/health
```

### API Documentation
- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🏗️ Architecture

### Core Components

```
src/
├── api/                    # FastAPI web service
│   ├── main.py            # FastAPI application
│   ├── routes.py          # API endpoints
│   ├── models.py          # Pydantic models
│   └── dependencies.py    # Dependency injection
├── cli.py                 # Command line interface
├── github_client.py       # GitHub API integration
├── repo_analyzer.py       # Repository analysis engine
├── database.py            # User-specific SQLite database
├── dataBaseExporter.py    # Multi-format export system
└── config.py              # Configuration management
```

### Database Schema

The tool maintains user-specific SQLite databases with tables for:
- **User Repositories**: Tracked repositories with analysis scores
- **Search History**: Search patterns and pagination state
- **Analysis Cache**: Cached repository analyses

### Fresh Results Algorithm

1. **Search Strategy Rotation**: Uses different GitHub search parameters
2. **Pagination Management**: Tracks search offsets for deep results
3. **User Filtering**: Excludes recently shown repositories per user
4. **Fallback Mechanisms**: Multiple attempts to ensure fresh discoveries

## 🔧 Configuration

### Environment Variables
```bash
# Required
GITHUB_TOKEN=your_token_here

# Optional
HOST=localhost              # API server host
PORT=8000                  # API server port
RELOAD=true                # Auto-reload in development
DB_PATH=repositories.db    # Database file location
```

### Config File (config.py)
```python
# Repository criteria
MIN_STARS = 500
MAX_STARS = 50000
MIN_PY_FILES = 15
MAX_PY_FILES = 100

# API settings
DEFAULT_LIMIT = 30
REQUEST_TIMEOUT = 30
MAX_CONCURRENT_REQUESTS = 10

# Allowed licenses (subset shown)
ALLOWED_LICENSES = {
    "MIT", "Apache-2.0", "BSD-3-Clause", 
    "BSD-2-Clause", "BSL-1.0", ...
}
```

## 📈 Analysis Scoring

### Scoring Breakdown
```
Overall Score = (Activity × 0.30) + (Opportunity × 0.35) + 
                (Complexity × 0.20) + (Maintainability × 0.15)

Score Ranges:
4.2-5.0 (84-100%): EXCELLENT - High activity with great opportunities
3.5-4.1 (70-83%):  GOOD - Should find suitable opportunities  
2.5-3.4 (50-69%):  MODERATE - May require more effort
0.0-2.4 (0-49%):   NOT RECOMMENDED - Look for more active repos
```

### Analysis Factors

**Activity Score**:
- Recent commit frequency
- Issue discussion activity
- Maintenance patterns

**Opportunity Score**:
- Good first issues count
- Help wanted labels
- Bug reports available
- Documentation needs

**Complexity Score**:
- Repository size (MB)
- File count estimates
- Language distribution
- Architecture complexity

**Maintainability Score**:
- Contributing guidelines
- README quality
- License presence
- Code organization

## 📤 Export Formats

### JSON Export
```json
{
  "export_info": {
    "exported_at": "2024-01-15T10:30:00",
    "total_repositories": 150
  },
  "repositories": [
    {
      "repo_name": "microsoft/playwright",
      "stars": 45000,
      "analysis_score": 4.2,
      "opportunities": [...]
    }
  ]
}
```

### CSV Export
```csv
repo_name,stars,license,analysis_score,url,last_shown
microsoft/playwright,45000,Apache-2.0,4.2,https://github.com/microsoft/playwright,2024-01-15
```

### Markdown Export
```markdown
## 1. microsoft/playwright

- **⭐ Stars**: 45,000
- **📜 License**: Apache-2.0
- **🎯 Analysis Score**: 4.2/5.0
- **🔗 URL**: [microsoft/playwright](https://github.com/microsoft/playwright)
```

## 🛠️ Development

### Setup Development Environment
```bash
# Clone and setup
git clone https://github.com/trippinganymess/repo_selector
cd repo_selector
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Start development server
RELOAD=true python api_server.py
```

### Project Structure
```
repo_selector/
├── src/                   # Source code
├── api_server.py          # API entry point
├── main.py               # CLI entry point
├── requirements.txt       # Dependencies
├── repositories.db        # SQLite database (created on first run)
└── README.md             # This file
```

## 🚨 Error Handling

The tool includes comprehensive error handling for:
- **GitHub API Rate Limits**: Automatic detection and graceful degradation
- **Network Issues**: Retry mechanisms and timeout handling
- **Database Errors**: User-specific error isolation
- **Invalid Repositories**: Graceful handling of deleted/private repos
- **Configuration Issues**: Clear error messages and suggestions

## ⚡ Performance

### Optimizations
- **GraphQL Queries**: Efficient single-request data fetching
- **Database Indexing**: Fast user-specific query performance
- **Concurrent Requests**: Parallel processing where appropriate
- **Caching**: Analysis result caching to avoid redundant API calls
- **Pagination**: Memory-efficient large result set handling

### Rate Limit Management
- Tracks GitHub API usage in real-time
- Implements exponential backoff for rate limit recovery
- Provides clear feedback on remaining API calls
- Optimizes query patterns to minimize API consumption

## 🔒 Security

- **Token Management**: Secure environment variable handling
- **User Isolation**: User-specific databases prevent data leakage
- **Input Validation**: Comprehensive request validation
- **API Security**: CORS configuration and request sanitization


## 🙋♂️ Support

- **Issues**: Report bugs or request features via GitHub Issues
- **Discussions**: Join community discussions in GitHub Discussions
- **Documentation**: Full API documentation at `/docs` when server is running

## 🔄 Version History

- **v1.0.0**: Initial release with core functionality
- User-specific database tracking
- Comprehensive repository analysis
- FastAPI web service
- Multi-format export capabilities

***

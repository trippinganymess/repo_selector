import uvicorn
import os
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from src.api.main import app
    from src.config import GITHUB_TOKEN
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running from the correct directory and have installed all dependencies:")
    print("pip install fastapi uvicorn pydantic python-multipart requests typer rich")
    sys.exit(1)

def main():
    """Main entry point for the API server"""
    
    # Print startup banner
    print("🚀 GitHub Repository Selector API")
    print("📦 Version: 1.0.0")
    print("=" * 50)
    
    # Basic environment check
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN environment variable not set")
        print("   Set it with: export GITHUB_TOKEN='your_token_here'")
        sys.exit(1)
    
    print("✅ Environment check passed")
    
    # Server configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    print(f"🌐 Starting server on http://{host}:{port}")
    print(f"📚 API docs will be available at http://localhost:{port}/docs")
    print(f"🏥 Health check at http://localhost:{port}/api/v1/health")
    print("=" * 50)
    
    try:
        uvicorn.run(
            "src.api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

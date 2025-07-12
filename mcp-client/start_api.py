#!/usr/bin/env python3
"""
Convenience script to start just the FastAPI server.
"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    # Run the deployment script in API mode
    deployment_script = Path(__file__).parent / "deployment" / "run_server.py"
    
    cmd = [sys.executable, str(deployment_script), "--mode", "api"]
    
    print("🚀 Starting MCP Client API Server...")
    print("Will be available at: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print()
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 API server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1) 
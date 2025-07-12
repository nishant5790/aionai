#!/usr/bin/env python3
"""
Convenience script to start both API and Web interface.
"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    # Run the deployment script in both mode
    deployment_script = Path(__file__).parent / "deployment" / "run_server.py"
    
    cmd = [sys.executable, str(deployment_script), "--mode", "both"]
    
    print("🚀 Starting MCP Client - Full Stack...")
    print("API Server: http://localhost:8000")
    print("Web Interface: http://localhost:8501")
    print("API Documentation: http://localhost:8000/docs")
    print()
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 All services stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1) 
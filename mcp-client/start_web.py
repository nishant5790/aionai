#!/usr/bin/env python3
"""
Convenience script to start just the Streamlit web interface.
"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    # Run the deployment script in web mode
    deployment_script = Path(__file__).parent / "deployment" / "run_server.py"
    
    cmd = [sys.executable, str(deployment_script), "--mode", "web"]
    
    print("🌐 Starting MCP Client Web Interface...")
    print("Will be available at: http://localhost:8501")
    print()
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 Web interface stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1) 
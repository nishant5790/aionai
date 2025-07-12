#!/usr/bin/env python3
"""
Deployment script for MCP Client.

This script starts the FastAPI backend and/or Streamlit frontend
for a complete MCP client deployment.
"""

import os
import sys
import time
import subprocess
import signal
import argparse
from pathlib import Path
from multiprocessing import Process

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def start_api_server(host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
    """Start the FastAPI server."""
    print(f"🚀 Starting MCP Client API on {host}:{port}")
    
    try:
        import uvicorn
        
        if debug:
            # Use app string for reload to work properly
            uvicorn.run(
                "mcp_client.api.app:app",
                host=host,
                port=port,
                log_level="debug",
                reload=True
            )
        else:
            # Use app object for production
            from mcp_client.api.app import app
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info",
                reload=False
            )
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        sys.exit(1)


def start_streamlit_app(port: int = 8501, api_url: str = "http://localhost:8000"):
    """Start the Streamlit web interface."""
    print(f"🌐 Starting Streamlit interface on port {port}")
    
    try:
        # Set API URL environment variable
        os.environ["API_BASE_URL"] = api_url
        
        # Get path to main.py
        main_path = Path(__file__).parent.parent / "src" / "mcp_client" / "web" / "main.py"
        
        if not main_path.exists():
            raise FileNotFoundError(f"Streamlit main.py not found at {main_path}")
        
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            str(main_path),
            "--server.port", str(port),
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--theme.base", "light"
        ]
        
        print(f"🔧 Running command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Streamlit: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error starting Streamlit: {e}")
        sys.exit(1)


def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description="Deploy MCP Client")
    parser.add_argument("--mode", choices=["api", "web", "both"], default="both",
                       help="Deployment mode (default: both)")
    parser.add_argument("--api-host", default="0.0.0.0", help="API host (default: 0.0.0.0)")
    parser.add_argument("--api-port", type=int, default=8000, help="API port (default: 8000)")
    parser.add_argument("--web-port", type=int, default=8501, help="Web interface port (default: 8501)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    print("🔗 MCP Client Deployment")
    print("=" * 50)
    print(f"Mode: {args.mode}")
    if args.mode in ["api", "both"]:
        print(f"API: http://{args.api_host}:{args.api_port}")
    if args.mode in ["web", "both"]:
        print(f"Web: http://localhost:{args.web_port}")
    print("=" * 50)
    
    processes = []
    
    try:
        if args.mode == "api":
            # Start only API server
            start_api_server(args.api_host, args.api_port, args.debug)
            
        elif args.mode == "web":
            # Start only Streamlit web interface
            api_url = f"http://{args.api_host}:{args.api_port}"
            start_streamlit_app(args.web_port, api_url)
            
        elif args.mode == "both":
            # Start both services in parallel
            print("🚀 Starting both API and Web services...")
            
            # Start API server in background process
            api_process = Process(
                target=start_api_server,
                args=(args.api_host, args.api_port, args.debug),
                name="MCP-API"
            )
            api_process.start()
            processes.append(api_process)
            print(f"✅ API server started (PID: {api_process.pid})")
            
            # Wait for API to start
            print("⏳ Waiting for API server to start...")
            time.sleep(3)
            
            # Start Streamlit web interface in background process
            api_url = f"http://{args.api_host}:{args.api_port}"
            web_process = Process(
                target=start_streamlit_app,
                args=(args.web_port, api_url),
                name="MCP-Web"
            )
            web_process.start()
            processes.append(web_process)
            print(f"✅ Web interface started (PID: {web_process.pid})")
            
            print("\n🎉 Both services are running!")
            print(f"📖 API Documentation: http://localhost:{args.api_port}/docs")
            print(f"🌐 Web Interface: http://localhost:{args.web_port}")
            print("\nPress Ctrl+C to stop all services...")
            
            # Wait for processes and handle shutdown
            try:
                # Monitor processes
                while True:
                    for process in processes:
                        if not process.is_alive():
                            print(f"⚠️  Process {process.name} stopped unexpectedly")
                            return
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n🛑 Shutting down services...")
                
                for process in processes:
                    if process.is_alive():
                        print(f"🔄 Stopping {process.name}...")
                        process.terminate()
                        process.join(timeout=5)
                        if process.is_alive():
                            print(f"⚠️  Force killing {process.name}...")
                            process.kill()
                
                print("✅ All services stopped")
                
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        
        # Clean up any running processes
        for process in processes:
            if process.is_alive():
                process.terminate()
        
        sys.exit(1)


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Startup script for BloomWatch with NASA API
This script starts the FastAPI server using the NASA data service as the primary data source.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Start BloomWatch with NASA API')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', default=8000, type=int, help='Port to bind to')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')
    args = parser.parse_args()

    # Get the directory containing this script
    script_dir = Path(__file__).parent
    api_dir = script_dir / "api"

    # Change to the project directory
    os.chdir(script_dir)

    # Set environment variables for NASA API
    os.environ['BLOOMWATCH_DATA_SOURCE'] = 'nasa'
    os.environ['BLOOMWATCH_DEFAULT_API'] = 'nasa'

    print("Starting BloomWatch with NASA API...")
    print(f"Data Source: NASA MODIS/GIBS")
    print(f"Server: http://{args.host}:{args.port}")
    print(f"Health Check: http://{args.host}:{args.port}/health")
    print(f"API Docs: http://{args.host}:{args.port}/docs")
    # Start the server
    cmd = [
        sys.executable, "-m", "uvicorn",
        "api.main_nasa:app",
        "--host", args.host,
        "--port", str(args.port)
    ]

    if args.reload:
        cmd.append("--reload")
        print("Auto-reload enabled for development")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nShutting down BloomWatch...")
    except subprocess.CalledProcessError as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

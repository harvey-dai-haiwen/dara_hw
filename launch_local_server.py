"""
Launch script for the dara_local_v2 web server.

This script starts the Dara Local v2 FastAPI app on port 8899, serving the
Vite+React frontend and the phase-search job queue API.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from dara_local_v2.server.app import launch_app


if __name__ == "__main__":
    print("=" * 72)
    print("Starting Dara Local v2 Web Server")
    print("=" * 72)
    print("Features:")
    print("  - Notebook Part 1 + Part 2 as a web workflow")
    print("  - Local ICSD/COD/MP phase-search with job queue")
    print("  - Multi-user submission by simple user tag")
    print("  - Plotly visualizations and downloadable reports")
    print()
    print("🌐 Open: http://localhost:8899/search")
    print("=" * 72)
    print()

    launch_app()

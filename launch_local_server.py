"""
Launch script for the dara_local server.

This script starts the extended Dara server on port 8899 with support for
local COD/ICSD/MP database selection.
"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from dara_local.server.app import launch_app

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Starting Dara Local Server")
    print("=" * 70)
    print("📊 Features:")
    print("  - Local database support: COD, ICSD, MP")
    print("  - Subset-based chemical system filtering")
    print("  - Custom CIF uploads")
    print("  - New endpoint: POST /api/search")
    print()
    print("🌐 Server will start on: http://localhost:8899")
    print("=" * 70)
    print()
    
    launch_app()

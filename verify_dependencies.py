#!/usr/bin/env python
"""
Verify all required dependencies for dara-xrd are importable.
This script checks that all critical packages can be imported.
"""

import sys
from pathlib import Path

def check_imports():
    """Check if all critical dependencies can be imported."""
    
    critical_imports = [
        # Core scientific computing
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("scipy", "scipy.signal"),
        ("sklearn", "scikit-learn"),
        
        # Crystallography and materials
        ("pymatgen", "pymatgen"),
        ("spglib", "spglib"),
        
        # Data handling
        ("pyarrow", "pyarrow"),
        ("pyarrow.parquet", "pyarrow"),
        
        # Plotting and visualization
        ("plotly", "plotly"),
        ("plotly.graph_objects", "plotly"),
        
        # Data processing
        ("asteval", "asteval"),
        ("xmltodict", "xmltodict"),
        ("toml", "toml"),
        
        # Tree and search structures
        ("treelib", "treelib"),
        ("jenkspy", "jenkspy"),
        
        # Web framework (for server)
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pydantic", "pydantic"),
        ("pydantic_settings", "pydantic-settings"),
        
        # Parallel processing
        ("ray", "ray"),
        ("jobflow", "jobflow"),
        
        # Other utilities
        ("dict2xml", "dict2xml"),
        ("pybaselines", "pybaselines"),
        ("montydb", "montydb"),
        ("rxn_network", "reaction-network"),
        ("mp_api", "mp_api"),
        
        # DARA itself
        ("dara", "dara-xrd"),
    ]
    
    print("=" * 70)
    print("DARA-XRD Dependency Verification")
    print("=" * 70)
    print(f"Python: {sys.version}")
    print(f"Path: {sys.executable}")
    print("=" * 70)
    
    failed_imports = []
    successful_imports = []
    
    for module_name, package_name in critical_imports:
        try:
            __import__(module_name)
            successful_imports.append((module_name, package_name))
            print(f"✅ {package_name:30s} OK")
        except ImportError as e:
            failed_imports.append((module_name, package_name, str(e)))
            print(f"❌ {package_name:30s} FAILED: {e}")
    
    print("\n" + "=" * 70)
    print(f"Summary: {len(successful_imports)}/{len(critical_imports)} packages OK")
    print("=" * 70)
    
    if failed_imports:
        print("\n⚠️  FAILED IMPORTS:")
        for module_name, package_name, error in failed_imports:
            print(f"  - {package_name}: {error}")
        print("\nTo fix, run:")
        print("  uv sync")
        return False
    else:
        print("\n✅ All critical dependencies are available!")
        return True

if __name__ == "__main__":
    success = check_imports()
    sys.exit(0 if success else 1)

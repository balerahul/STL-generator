#!/usr/bin/env python3
"""
STL Grid Generator - Main Entry Point

This script provides the same functionality as the installed binary version
without requiring installation via pip. Users can run this directly from
the source directory.

Usage:
    python main.py --help
    python main.py --config examples/basic_grid.yaml
    python main.py --nx 3 --ny 2 --W 10 --H 8 --sx 0.7 --sy 0.7

    # Or make it executable and run directly:
    chmod +x main.py
    ./main.py --config examples/basic_grid.yaml

Requirements:
    - Python 3.7+
    - numpy
    - PyYAML
"""

import sys
import os
from pathlib import Path

# Add the package directory to Python path so we can import the modules
package_dir = Path(__file__).parent / "stl_grid_generator"
if package_dir.exists():
    sys.path.insert(0, str(Path(__file__).parent))
else:
    print(f"Error: Could not find stl_grid_generator package at {package_dir}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)

try:
    from stl_grid_generator.cli import main
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("\nMake sure you have the required dependencies installed:")
    print("  pip install numpy PyYAML")
    print("\nOr install the full package:")
    print("  pip install -e .")
    sys.exit(1)

if __name__ == "__main__":
    main()
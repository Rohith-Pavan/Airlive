#!/usr/bin/env python3
"""
GoLive Studio - Debug Version with Enhanced Logging
"""

import sys
import os
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Enable debug logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('golive_debug.log')
    ]
)

print("=" * 60)
print("GoLive Studio - Debug Mode")
print("=" * 60)
print("All debug output will be saved to 'golive_debug.log'")
print("=" * 60)

# Import and run the main application
from main import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

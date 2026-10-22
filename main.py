#!/usr/bin/env python3
"""
Memory-Limited Duplicate Event Detector Using Bloom Filter and Hash Functions
Data Structures & Algorithms (DSA) Case Study

Entry Point:
    python main.py
"""

import sys
import os

# Ensure the root directory is on the module search path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.ui.console_app import ConsoleApp


def main():
    try:
        app = ConsoleApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\n[!] Program interrupted by user. Exiting cleanly...")
        sys.exit(0)


if __name__ == "__main__":
    main()

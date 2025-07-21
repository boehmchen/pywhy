"""
Main entry point for running Python Whyline as a module.
Usage: python -m python_whyline [filename]
"""

import sys
from .cli import main

if __name__ == "__main__":
    main()
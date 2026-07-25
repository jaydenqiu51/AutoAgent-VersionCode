"""Launch the AI Coding Agent Framework GUI (no console window).

Double-click this file on Windows to start the app without any terminal.
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aicoder.gui import main

main()

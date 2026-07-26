"""Launch the AutoAgent GUI (no console window).

Double-click this file on Windows to start the app without any terminal.
If anything goes wrong, an error dialog is shown instead of failing silently.
"""
import sys
import traceback
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from aicoder.gui import main
    main()
except Exception:
    # Show the error in a dialog — pythonw has no console to print to
    err = traceback.format_exc()
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        if "ModuleNotFoundError" in err or "ImportError" in err:
            messagebox.showerror(
                "AutoAgent — Missing Dependencies",
                "Some required packages are not installed.\n\n"
                "Fix: double-click run.bat instead — it installs\n"
                "everything automatically on first run.\n\n"
                "Or open a terminal in this folder and run:\n"
                "    pip install -r requirements.txt\n\n"
                f"Details:\n{err.splitlines()[-1]}")
        else:
            messagebox.showerror("AutoAgent — Startup Error", err[-1500:])
    except Exception:
        pass
    raise

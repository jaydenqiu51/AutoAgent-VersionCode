"""Build script — packages the AI Coding Agent Framework into a standalone .exe.

Requires PyInstaller: pip install pyinstaller

Usage:
    python build.py          # Build the desktop app .exe
    python build.py --cli    # Build the CLI .exe
    python build.py --clean  # Clean build artifacts

Output goes to dist/ folder.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def clean():
    """Remove build artifacts."""
    for d in ["build", "dist", "__pycache__"]:
        path = ROOT / d
        if path.exists():
            shutil.rmtree(path)
    for spec in ROOT.glob("*.spec"):
        spec.unlink()
    print("Cleaned build artifacts.")


def build_gui():
    """Build the desktop GUI app into a single .exe."""
    print("Building Desktop GUI...")

    gui_script = ROOT / "aicoder" / "gui.py"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",  # No console window
        "--name", "AICoder",
        "--add-data", f"{ROOT / 'aicoder'}{os.pathsep}aicoder",
        "--hidden-import", "openai",
        "--hidden-import", "anthropic",
        "--hidden-import", "dotenv",
        "--hidden-import", "requests",
        "--hidden-import", "google.generativeai",
        "--hidden-import", "tkinter",
        "--hidden-import", "queue",
        str(gui_script),
    ]

    subprocess.run(cmd, cwd=str(ROOT), check=True)
    print(f"\nBuild complete! Output: {ROOT / 'dist' / 'AICoder.exe'}")


def build_cli():
    """Build the CLI app into a single .exe."""
    print("Building CLI...")

    cli_script = ROOT / "aicoder" / "cli.py"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        "--name", "aicoder",
        "--add-data", f"{ROOT / 'aicoder'}{os.pathsep}aicoder",
        "--hidden-import", "openai",
        "--hidden-import", "anthropic",
        "--hidden-import", "dotenv",
        "--hidden-import", "requests",
        str(cli_script),
    ]

    subprocess.run(cmd, cwd=str(ROOT), check=True)
    print(f"\nBuild complete! Output: {ROOT / 'dist' / 'aicoder.exe'}")


def main():
    parser = argparse.ArgumentParser(description="Build AI Coding Agent Framework executables")
    parser.add_argument("--cli", action="store_true", help="Build CLI .exe instead of GUI")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts only")

    args = parser.parse_args()

    if args.clean:
        clean()
        return

    # Check for PyInstaller
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is not installed. Install it with:")
        print("  pip install pyinstaller")
        sys.exit(1)

    clean()

    if args.cli:
        build_cli()
    else:
        build_gui()


if __name__ == "__main__":
    main()

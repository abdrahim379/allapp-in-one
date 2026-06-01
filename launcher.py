#!/usr/bin/env python3
"""
ALL APP IN ONE — Launcher
Run:  python3 launcher.py
"""
import subprocess, sys, os
from pathlib import Path

APP  = Path(__file__).parent / "app.py"
REQS = Path(__file__).parent / "requirements.txt"

print("=" * 48)
print("   🚀  ALL APP IN ONE — Launcher")
print("=" * 48)

print("\n📦 Installing dependencies...\n")
subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(REQS), "--progress-bar","on"])
print("\n✅ Ready!\n")

print("🚀 Launching app...\n")
os.chdir(Path(__file__).parent)
try:
    subprocess.run(["streamlit", "run", str(APP)])
except KeyboardInterrupt:
    print("\n\n👋 App stopped. Run python3 launcher.py to restart.\n")

"""
Sets up an isolated Python environment for the BRAMBLE notebook.
Run this ONCE from inside your BRAMBLE folder, using your normal (non-venv) Python:

    python setup_bramble_env.py

It creates a venv/ folder, installs everything the notebook needs,
and registers it as a Jupyter kernel VS Code can select.
"""

import subprocess
import sys
import os
from pathlib import Path

VENV_DIR = Path("venv")
PACKAGES = [
    "pymc",
    "arviz",
    "numpy",
    "pandas",
    "matplotlib",
    "seaborn",
    "scikit-learn",
    "scipy",
    "jupyter",
    "ipykernel",
]
KERNEL_NAME = "bramble-env"
KERNEL_DISPLAY_NAME = "BRAMBLE (venv)"


def run(cmd):
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        sys.exit(1)


def main():
    # 1. Create the venv if it doesn't already exist
    if VENV_DIR.exists():
        print(f"'{VENV_DIR}' already exists — skipping creation.")
    else:
        print(f"Creating virtual environment in '{VENV_DIR}'...")
        run([sys.executable, "-m", "venv", str(VENV_DIR)])

    # 2. Find the venv's own python/pip (works without "activating" anything)
    if os.name == "nt":
        venv_python = VENV_DIR / "Scripts" / "python.exe"
    else:
        venv_python = VENV_DIR / "bin" / "python"

    if not venv_python.exists():
        print(f"Could not find {venv_python} — venv creation may have failed.")
        sys.exit(1)

    # 3. Upgrade pip, then install everything the notebook needs
    run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(venv_python), "-m", "pip", "install"] + PACKAGES)

    # 4. Register this environment as a Jupyter kernel VS Code can select
    run([
        str(venv_python), "-m", "ipykernel", "install", "--user",
        f"--name={KERNEL_NAME}", f"--display-name={KERNEL_DISPLAY_NAME}",
    ])

    print("\nDone.")
    print(f"In VS Code, open the notebook, click 'Select Kernel', "
          f"and choose '{KERNEL_DISPLAY_NAME}'.")


if __name__ == "__main__":
    main()

import os
import sys
import subprocess

def build():
    # Ensure dependencies are installed
    # pip install pyinstaller
    
    app_name = "PipeLRAStudio"
    entry_point = "src/main.py"
    
    # PyInstaller Command
    # --noconsole: Don't show terminal window
    # --onefile: Pack everything into one .exe (can be slow to start, --onedir is faster but messy)
    # --collect-all: Ensure all shared libraries for complex packages are included
    
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--name", app_name,
        "--collect-all", "vtk",
        "--collect-all", "PySide6",
        "--hidden-import", "fpdf2",
        "--hidden-import", "numpy",
        "--clean",
        entry_point
    ]
    
    print(f"Starting build for {app_name}...")
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "="*50)
        print(f"BUILD SUCCESSFUL!")
        print(f"Executable can be found in the 'dist' folder.")
        print("="*50)
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
    except FileNotFoundError:
        print("PyInstaller not found. Please install it with: pip install pyinstaller")

if __name__ == "__main__":
    build()

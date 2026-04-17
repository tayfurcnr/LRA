import os
import subprocess

def build():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    spec_path = os.path.join(repo_root, "PipeLRAStudio.spec")

    cmd = [
        "pyinstaller",
        "--clean",
        spec_path,
    ]
    
    print("Starting build for PipeLRAStudio...")
    try:
        subprocess.run(cmd, check=True, cwd=repo_root)
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

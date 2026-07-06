import os
import sys
import subprocess
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_cmd(cmd, cwd=None):
    print(f"Running: {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd)
    if res.returncode != 0:
        print(f"Error: Command failed with exit code {res.returncode}")
        sys.exit(res.returncode)

def main():
    print("====================================================")
    # 1. Build Frontend
    print("Step 1: Building React/Vite frontend...")
    frontend_dir = os.path.join(PROJECT_ROOT, "frontend", "artifacts", "astrogen")
    # Set env vars for production build
    os.environ["PORT"] = "5173"
    os.environ["BASE_PATH"] = "/"
    try:
        print("Running: npm run build")
        res = subprocess.run("npm run build", shell=True, cwd=frontend_dir)
        if res.returncode != 0:
            print("Warning: npm run build failed. Checking if pre-built assets exist...")
            if not os.path.exists(os.path.join(frontend_dir, 'dist', 'public')):
                print("Error: Pre-built assets not found in dist/public, and build failed.")
                sys.exit(res.returncode)
            else:
                print("Using existing pre-built assets from dist/public.")
        else:
            print("Frontend compiled successfully.")
    except Exception as e:
        print(f"Warning: Failed to compile frontend: {e}. Checking if pre-built assets exist...")
        if not os.path.exists(os.path.join(frontend_dir, 'dist', 'public')):
            print("Error: Pre-built assets not found in dist/public.")
            sys.exit(1)
        else:
            print("Using existing pre-built assets from dist/public.")

    # 2. Package with PyInstaller
    print("\nStep 2: Compiling standalone executable with PyInstaller...")
    # Clean old builds
    dist_path = os.path.join(PROJECT_ROOT, "dist")
    build_path = os.path.join(PROJECT_ROOT, "build")
    if os.path.exists(dist_path):
        shutil.rmtree(dist_path)
    if os.path.exists(build_path):
        shutil.rmtree(build_path)

    # Compile command
    # We add only the static compiled frontend assets and run main.py (PyInstaller compiles backend imports automatically)
    pyinstaller_cmd = (
        f"\"{sys.executable}\" -m PyInstaller --console --name AstroGen "
        f"--paths \"{PROJECT_ROOT}\" "
        f"--icon \"{os.path.join(PROJECT_ROOT, 'frontend', 'logo.ico')}\" "
        f"--additional-hooks-dir \"{os.path.join(PROJECT_ROOT, 'scripts', 'hooks')}\" "
        f"--exclude-module torch.utils.benchmark.utils.valgrind_wrapper "
        f"--exclude-module torch.utils.benchmark "
        f"--add-data \"{os.path.join(frontend_dir, 'dist', 'public')};backend/dist\" "
        f"--add-data \"{os.path.join(PROJECT_ROOT, 'frontend', 'logo.ico')};frontend\" "
        f"--add-data \"{os.path.join(PROJECT_ROOT, '.env')};.\" "
        f"--add-data \"{os.path.join(PROJECT_ROOT, 'backend')};backend\" "
        f"\"{os.path.join(PROJECT_ROOT, 'frontend', 'main.py')}\""
    )
    run_cmd(pyinstaller_cmd, cwd=PROJECT_ROOT)

    # 3. Setup visible data folders for users
    print("\nStep 3: Initializing visible user data directories...")
    exe_dist_dir = os.path.join(PROJECT_ROOT, "dist", "AstroGen")
    visible_data_dir = os.path.join(exe_dist_dir, "data", "generated")
    os.makedirs(visible_data_dir, exist_ok=True)

    print("\n====================================================")
    print(" SUCCESS: Standalone AstroGen application built!")
    print(f" Executable is available in: {os.path.join(exe_dist_dir, 'AstroGen.exe')}")
    print("====================================================")

if __name__ == "__main__":
    main()

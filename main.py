import sys
import os

print("\n--- AGGRESSIVE RENDER DIAGNOSTIC ---")
try:
    cwd = os.getcwd()
    print(f"Current Working Directory (CWD): {cwd}")

    # Check what files are visible to the OS
    files = os.listdir(cwd)
    print(f"Files in CWD: {files}")

    # Check if backend is a folder or something else
    if "backend" in files:
        backend_path = os.path.join(cwd, "backend")
        print(f"Backend is a directory: {os.path.isdir(backend_path)}")
        print(f"Contents of backend/: {os.listdir(backend_path)}")
    else:
        print("!! CRITICAL: 'backend' folder is MISSING from CWD !!")

    # Force path injection
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    print(f"Final sys.path: {sys.path}")

    from backend.main import app

    print("SUCCESS: backend.main imported successfully.")
except Exception as e:
    print(f"FAILURE: Import failed. Error: {e}")
    # Don't let it crash silently, we need these logs!
    raise e

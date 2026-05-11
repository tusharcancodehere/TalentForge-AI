import sys
import os


# 1. Absolute Path Injection
root_path = os.path.dirname(os.path.abspath(__file__))
if root_path not in sys.path:
    sys.path.insert(0, root_path)


# 2. Render Environment Diagnostics
print("--- STARTING RENDER DEPLOYMENT DIAGNOSTIC ---")
print(f"Current Working Directory: {os.getcwd()}")
print(f"Python Search Path: {sys.path}")
try:
    print(f"Root Directory Contents: {os.listdir(root_path)}")
    backend_dir = os.path.join(root_path, "backend")
    if os.path.exists(backend_dir):
        print(f"Backend Folder Found. Contents: {os.listdir(backend_dir)}")
    else:
        print("!! CRITICAL: 'backend' folder not found in root !!")
except Exception as e:
    print(f"Diagnostic Error: {e}")
print("---------------------------------------------")


# 3. Secure Import
try:
    from backend.main import app

    print("V3 Protocol: Backend Linkage Successful.")
except ImportError as e:
    print(f"V3 Protocol: Linkage Failed. Detail: {e}")
    raise e

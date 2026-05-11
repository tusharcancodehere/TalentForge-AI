import sys
import os

# 1. Absolute Path Injection
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 2. Render Hardware/FS Audit (Visible in Logs)
print("\n--- RENDER SYSTEM AUDIT ---")
print(f"CWD: {os.getcwd()}")
print(f"Sys Path: {sys.path}")
try:
    items = os.listdir(BASE_DIR)
    print(f"Root Contents: {items}")
    if "backend" in items:
        print(f"Backend Found. Contents: {os.listdir(os.path.join(BASE_DIR, 'backend'))}")
    else:
        print("!! ERROR: 'backend' FOLDER NOT FOUND IN ROOT !!")
except Exception as e:
    print(f"Diagnostic Crash: {e}")
print("---------------------------\n")

# 3. Secure Import
try:
    from backend.main import app
    print("V3 Protocol: Linkage Successful.")
except ImportError as e:
    print(f"V3 Protocol: Linkage Failed. Error: {e}")
    raise e

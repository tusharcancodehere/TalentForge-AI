import sys
import os

# Force the current directory into the python path for Linux compatibility
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.main import app

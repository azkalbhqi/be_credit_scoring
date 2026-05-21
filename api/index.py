import sys
import os

# Add the parent directory to the system path so Python can find main.py and other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

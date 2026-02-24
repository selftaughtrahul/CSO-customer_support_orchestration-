import sys
import os

# Add the project root to the path so pytest can import 'core', 'agents', 'tools', etc.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

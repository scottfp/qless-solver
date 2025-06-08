import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
cli_path = os.path.join(project_root, "cli")
if cli_path not in sys.path:
    sys.path.insert(0, cli_path)

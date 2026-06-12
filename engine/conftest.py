import sys, pathlib

# Add engine/ to sys.path so `grounding` package is importable
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

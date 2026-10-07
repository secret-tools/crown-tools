"""URL Decode — FR entry point."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from lib.runner import run_tool
if __name__=='__main__':run_tool('url-decode','fr')

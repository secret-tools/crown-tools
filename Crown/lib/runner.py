"""Run a tool inside the common terminal interface."""
from .entry import run_crown

def run_tool(tool_id,language):
    run_crown(['--tool',tool_id,'--lang',language])

"""
Custom MCP Server: Exposes the user's resume.txt as a readable tool.
Built with FastMCP. Run this separately: python mcp_servers/resume_server.py
"""
import os
from fastmcp import FastMCP

mcp = FastMCP(
    name="resume-file-server"
)

@mcp.tool()
def read_resume() -> str:
    """Read the user's resume from resume.txt and return the full text."""
    resume_path = os.getenv("RESUME_PATH", "./resume.txt")
    
    if not os.path.exists(resume_path):
        return "ERROR: resume.txt not found. Place your resume as resume.txt in project root."
    
    with open(resume_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    
    if len(content) < 50:
        return "ERROR: resume.txt is empty or too short. Please add your resume content."
    
    # Limit to 5000 chars to prevent overloading the context window
    return content[:5000]

if __name__ == "__main__":
    mcp.run()

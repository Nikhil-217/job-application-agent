import os
import sys
import logging

# Force all root logging handlers to write to stderr so they don't pollute stdout (which is used for MCP JSON-RPC)
root_logger = logging.getLogger()
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Add a stderr handler explicitly
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("%(message)s"))
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

# Import and run the Google Sheets MCP server
from mcp_google_sheets import main

if __name__ == "__main__":
    main()

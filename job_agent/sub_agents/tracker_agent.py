"""
TrackerAgent: Logs job applications to Google Sheets via MCP.
"""
import os
from datetime import datetime
from google.adk import Agent
from dotenv import load_dotenv

import sys
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioServerParameters, StdioConnectionParams

load_dotenv()

# Get absolute path of sheets_server.py and service account file to avoid relative path resolution issues
base_dir = os.path.abspath(os.path.dirname(__file__))
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./service_account.json")
if not os.path.isabs(creds_path):
    creds_path = os.path.abspath(os.path.join(base_dir, "..", "..", creds_path))

sheets_server_path = os.path.abspath(os.path.join(base_dir, "..", "..", "mcp_servers", "sheets_server.py"))

# Create the MCP toolset synchronously at module load time.
sheets_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[sheets_server_path],
            env={
                "GOOGLE_APPLICATION_CREDENTIALS": creds_path,
            }
        )
    )
)

tracker_agent = Agent(
    name="tracker_agent",
    model="gemini-3.1-flash-lite",
    description="Logs job applications to Google Sheets tracker",
    instruction=f"""
You are an application tracking agent.

When asked to log an application, prepare a row with these columns in order:
1. Applied Date: The current date in YYYY-MM-DD format (read this from the request context, e.g. "Today is YYYY-MM-DD")
2. Company: The company name from the job analysis
3. Role: The job title/role from the job analysis  
4. Resume Version: "Tailored PDF"
5. Status: "Applied"
6. Last Date to Apply: The application deadline from the job analysis (e.g. YYYY-MM-DD or "Not specified")
7. JD Description in few words: The brief 1-sentence job summary from the job analysis (max 100 characters)

Use the Google Sheets MCP tool (specifically add_rows) to append this row to the spreadsheet.
Spreadsheet ID: {os.getenv("SPREADSHEET_ID", "SET_IN_ENV")}
Sheet name: {os.getenv("SHEET_NAME", "Sheet1")}

Always confirm: "Logged: [Company] - [Role] on [Applied Date]" after successful write.

GUARDRAILS:
- Only append rows, never delete or edit existing rows
- Redact any phone numbers, emails, or Aadhaar numbers from the description field
- If the tool fails, report the error details clearly
""",
    tools=[sheets_toolset],
)

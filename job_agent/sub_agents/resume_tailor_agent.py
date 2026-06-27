"""
ResumeTailorAgent: Rewrites resume bullet points to match a job description.
Uses the Resume File MCP server to read the user's resume.
"""
import os
import asyncio
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioServerParameters, StdioConnectionParams
import sys

# Get absolute path of resume_server.py to avoid relative path resolution issues
base_dir = os.path.abspath(os.path.dirname(__file__))
resume_server_path = os.path.abspath(os.path.join(base_dir, "..", "..", "mcp_servers", "resume_server.py"))

# Create the MCP toolset synchronously at module load time.
resume_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[resume_server_path],
            env={"RESUME_PATH": os.getenv("RESUME_PATH", "./resume.txt")}
        )
    )
)

def generate_and_upload_resume_pdf(tailored_text: str, company: str, role: str) -> str:
    """
    Generates a beautifully formatted PDF from the tailored resume text,
    and uploads it directly to Google Drive.
    
    Args:
        tailored_text: The complete tailored resume text (in markdown).
        company: The name of the hiring company.
        role: The exact job title/role.
        
    Returns:
        A status string indicating the version name, filename, and Google Drive view link.
    """
    from datetime import datetime
    base_dir = os.path.abspath(os.path.dirname(__file__))
    local_pdf_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "tailored_resumes"))
    os.makedirs(local_pdf_dir, exist_ok=True)
    
    # Temporary filename
    temp_filename = f"temp_resume_{int(datetime.now().timestamp())}.pdf"
    temp_pdf_path = os.path.join(local_pdf_dir, temp_filename)
    
    try:
        # 1. Generate PDF locally
        from job_agent.utils.pdf_generator import generate_resume_pdf
        generate_resume_pdf(tailored_text, temp_pdf_path)
        
        # 2. Upload to Google Drive
        from job_agent.utils.google_drive_uploader import upload_resume_to_drive
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./service_account.json")
        if not os.path.isabs(creds_path):
            creds_path = os.path.abspath(os.path.join(base_dir, "..", "..", creds_path))
            
        drive_result = upload_resume_to_drive(
            pdf_path=temp_pdf_path,
            company=company,
            role=role,
            service_account_path=creds_path
        )
        
        if drive_result.get('success'):
            version_label = drive_result.get('version_label')
            final_filename = drive_result.get('filename')
            drive_link = drive_result.get('drive_link')
            
            # Rename local PDF to match the Drive filename
            final_pdf_path = os.path.join(local_pdf_dir, final_filename)
            if os.path.exists(temp_pdf_path):
                if os.path.exists(final_pdf_path):
                    os.remove(final_pdf_path)
                os.rename(temp_pdf_path, final_pdf_path)
                
            return f"SUCCESS: Tailored resume PDF generated and uploaded to Google Drive as '{version_label}'. File Name: '{final_filename}'. Link: {drive_link}."
        else:
            raise Exception(drive_result.get('error', 'Unknown upload error'))
    except Exception as e:
        # Cleanup temp file on error
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except:
                pass
        return f"ERROR: Failed to generate or upload PDF: {str(e)}"

resume_tailor_agent = Agent(
    name="resume_tailor_agent",
    model="gemini-3.1-flash-lite",
    description="Tailors resume bullet points to match a job description",
    instruction="""
You are a professional resume writer specialising in ATS optimisation.

Steps:
1. Use the read_resume tool to fetch the user's resume.
2. Review the job analysis provided by the previous agent.
3. Identify the relevant sections (the professional summary and the experience bullet points) and rewrite them to naturally incorporate the ATS keywords.
4. Output the **COMPLETE, FULL TAILORED RESUME** from start to finish. Keep all other sections (like education, skills, contact info, job titles, and unmodified bullet points) exactly as they are in the original resume.
5. Immediately after generating the tailored resume, call the generate_and_upload_resume_pdf tool. Provide it with the tailored resume text, the company name, and the role title.
6. Present the complete tailored resume text first, and then clearly end your message by reporting the version label (e.g. `Resume_v1`, `Resume_v2`) and the Google Drive view link (e.g. "Google Drive Upload: [version_label] - [Link]").

Output format:
Start directly with the candidate's name as a heading (e.g. `# Nikhil Pamu`), followed by contact info, and then each section starting with `## [Section Name]`.
Ensure the entire resume is represented in the output so it can be generated as a full document.

GUARDRAILS:
- Only rephrase existing experience — NEVER invent new experience.
- Do not change job titles, company names, dates, or contact details.
- Keep all bullet points truthful and accurate.
""",
    tools=[resume_toolset, generate_and_upload_resume_pdf],
)

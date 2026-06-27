"""
Gradio Web Interface for the Job Application Assistant Dashboard.
Provides a structured step-by-step workflow with PDF generation and Sheets logging.
"""
import os
import re
import asyncio
import gradio as gr
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Ensure GEMINI_API_KEY is mapped
if os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

# Import agents
from job_agent.sub_agents.job_analysis_agent import job_analysis_agent
from job_agent.sub_agents.resume_tailor_agent import resume_tailor_agent
from job_agent.sub_agents.cover_letter_agent import cover_letter_agent
from job_agent.sub_agents.tracker_agent import tracker_agent
from job_agent.sub_agents.followup_agent import followup_agent

# Import PDF generator
from job_agent.utils.pdf_generator import generate_resume_pdf

APP_NAME = "job_application_dashboard"
session_service = InMemorySessionService()

# Create separate runners for modular execution
analysis_runner = Runner(agent=job_analysis_agent, app_name=APP_NAME, session_service=session_service)
tailor_runner = Runner(agent=resume_tailor_agent, app_name=APP_NAME, session_service=session_service)
cover_letter_runner = Runner(agent=cover_letter_agent, app_name=APP_NAME, session_service=session_service)
tracker_runner = Runner(agent=tracker_agent, app_name=APP_NAME, session_service=session_service)
followup_runner = Runner(agent=followup_agent, app_name=APP_NAME, session_service=session_service)

# Security checks
from security.input_validator import rate_limit_check, sanitise_input, validate_job_description


async def run_agent_helper(runner_instance, message_text: str, session_id: str) -> str:
    """Helper to execute an agent run asynchronously and return the text."""
    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=message_text)]
    )
    final_response = ""
    async for event in runner_instance.run_async(
        user_id="user",
        session_id=session_id,
        new_message=content
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response = event.content.parts[0].text
                break
    return final_response


async def analyze_job_desc(jd_text: str, state: dict):
    """Step 1: Analyze Job Description"""
    # Security checks
    allowed, rate_msg = rate_limit_check()
    if not allowed:
        return f"⚠️ {rate_msg}", "", "", "", "", state
        
    clean_jd, warnings = sanitise_input(jd_text)
    
    is_valid, validation_msg = validate_job_description(clean_jd)
    if not is_valid:
        return f"⚠️ {validation_msg}", "", "", "", "", state
        
    session_id = f"analysis_{int(datetime.now().timestamp())}"
    await session_service.create_session(app_name=APP_NAME, user_id="user", session_id=session_id)
    
    try:
        result_text = await run_agent_helper(analysis_runner, clean_jd, session_id)
        
        # Parse fields from the agent response using regex
        company = "Not specified"
        role = "Not specified"
        deadline = "Not specified"
        summary = "Not specified"
        
        comp_match = re.search(r"\*\*\s*Company Name\s*\*\*\s*:\s*(.*)", result_text, re.IGNORECASE)
        if comp_match:
            company = comp_match.group(1).strip()
            
        role_match = re.search(r"\*\*\s*Role Title\s*\*\*\s*:\s*(.*)", result_text, re.IGNORECASE)
        if role_match:
            role = role_match.group(1).strip()
            
        deadline_match = re.search(r"\*\*\s*Last Date to Apply\s*\*\*\s*:\s*(.*)", result_text, re.IGNORECASE)
        if deadline_match:
            deadline = deadline_match.group(1).strip()
            
        summary_match = re.search(r"\*\*\s*JD Summary\s*\*\*\s*:\s*(.*)", result_text, re.IGNORECASE)
        if summary_match:
            summary = summary_match.group(1).strip()
            
        # Update State
        state["jd_text"] = clean_jd
        state["analysis_result"] = result_text
        state["company_name"] = company
        state["role_title"] = role
        state["last_date_to_apply"] = deadline
        state["jd_summary"] = summary
        
        return result_text, company, role, deadline, summary, state
    except Exception as e:
        return f"Error: {str(e)}", "", "", "", "", state


def load_original_resume():
    """Load resume.txt file content"""
    resume_path = os.getenv("RESUME_PATH", "./resume.txt")
    if os.path.exists(resume_path):
        with open(resume_path, "r", encoding="utf-8") as f:
            return f.read()
    return "resume.txt not found. Please place your resume in the project root."


async def tailor_resume_action(resume_text: str, state: dict):
    """Step 2: Tailor Resume & Generate PDF"""
    if "jd_text" not in state or not state["jd_text"]:
        return "Please analyze a job description in Tab 1 first.", None, state, "Tailored PDF"
        
    session_id = f"tailor_{int(datetime.now().timestamp())}"
    await session_service.create_session(app_name=APP_NAME, user_id="user", session_id=session_id)
    
    prompt = f"""
    Please tailor my resume for the job description.
    Job Analysis: {state['analysis_result']}
    Original Resume Content:
    {resume_text}
    """
    
    try:
        tailored_text = await run_agent_helper(tailor_runner, prompt, session_id)
        
        # Scan local directory for the latest PDF file generated by the agent tool
        import glob
        pdf_dir = "./tailored_resumes"
        list_of_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
        pdf_path = max(list_of_files, key=os.path.getctime) if list_of_files else None
        
        # Extract version label and drive link from agent output
        version_label = "Tailored PDF"
        drive_link = None
        
        link_match = re.search(r"https://drive\.google\.com/[^\s\)\"\']+", tailored_text)
        if link_match:
            drive_link = link_match.group(0)
            
        ver_match = re.search(r"Resume_v\d+", tailored_text)
        if ver_match:
            version_label = ver_match.group(0)
        elif pdf_path:
            # Fallback to parsing filename
            fn_match = re.search(r"Resume_v\d+", os.path.basename(pdf_path))
            if fn_match:
                version_label = fn_match.group(0)
                
        # Update State
        state["tailored_resume"] = tailored_text
        state["pdf_path"] = pdf_path
        state["resume_version_label"] = version_label
        if drive_link:
            state["drive_link"] = drive_link
            
        return tailored_text, pdf_path, state, version_label
    except Exception as e:
        return f"Error during tailoring: {str(e)}", None, state, "Tailored PDF"


async def generate_cover_letter_action(state: dict):
    """Step 3: Generate Cover Letter"""
    if "jd_text" not in state or not state["jd_text"]:
        return "Please analyze a job description in Tab 1 first.", state
    if "tailored_resume" not in state or not state["tailored_resume"]:
        return "Please tailor your resume in Tab 2 first.", state
        
    session_id = f"cover_{int(datetime.now().timestamp())}"
    await session_service.create_session(app_name=APP_NAME, user_id="user", session_id=session_id)
    
    prompt = f"""
    Write a cover letter based on:
    Job Analysis: {state['analysis_result']}
    Tailored Resume Content:
    {state['tailored_resume']}
    """
    
    try:
        letter_text = await run_agent_helper(cover_letter_runner, prompt, session_id)
        state["cover_letter"] = letter_text
        return letter_text, state
    except Exception as e:
        return f"Error: {str(e)}", state


async def log_to_sheets_action(date: str, company: str, role: str, status: str, version: str, deadline: str, summary: str, state: dict):
    """Step 4: Log to Google Sheets Tracker"""
    session_id = f"tracker_{int(datetime.now().timestamp())}"
    await session_service.create_session(app_name=APP_NAME, user_id="user", session_id=session_id)
    
    prompt = f"""
    Please log this application row to Sheets:
    - Today is {date}
    - Company Name: {company}
    - Role Title: {role}
    - Resume Version: {version}
    - Status: {status}
    - Last Date to Apply: {deadline}
    - JD Summary: {summary}
    """
    
    try:
        log_response = await run_agent_helper(tracker_runner, prompt, session_id)
        state["logged_status"] = log_response
        return log_response, state
    except Exception as e:
        return f"Error: {str(e)}", state


async def generate_followup_action(state: dict):
    """Step 5: Generate Follow-up Email"""
    if "company_name" not in state or not state["company_name"]:
        return "Please analyze a job description in Tab 1 first.", state
        
    session_id = f"followup_{int(datetime.now().timestamp())}"
    await session_service.create_session(app_name=APP_NAME, user_id="user", session_id=session_id)
    
    prompt = f"Generate follow-up email for the role of {state['role_title']} at {state['company_name']}."
    
    try:
        email_text = await run_agent_helper(followup_runner, prompt, session_id)
        state["followup_email"] = email_text
        return email_text, state
    except Exception as e:
        return f"Error: {str(e)}", state


# UI Definition
with gr.Blocks(title="Job Application Dashboard") as demo:
    state_store = gr.State(value={})
    
    gr.Markdown("""
    # 🎯 Job Application Tailor & Tracker Dashboard
    **A structured multi-agent workspace to analyze job postings, tailor resumes to PDF, draft cover letters, and log to Google Sheets.**
    """)
    
    with gr.Tabs():
        # TAB 1: Job Description Analyzer
        with gr.TabItem("📋 1. Job Analyzer"):
            gr.Markdown("### Paste a job description to extract core details and ATS keywords.")
            with gr.Row():
                jd_input = gr.Textbox(
                    label="Job Description Text", 
                    placeholder="Paste the full job posting here...", 
                    lines=12
                )
            with gr.Row():
                analyze_btn = gr.Button("Analyze Job Posting", variant="primary")
            
            with gr.Row():
                analysis_output = gr.Markdown(label="Analysis Result")
            
            # Hidden fields to share values with Tab 4 (Tracker)
            company_field = gr.Textbox(visible=False)
            role_field = gr.Textbox(visible=False)
            deadline_field = gr.Textbox(visible=False)
            summary_field = gr.Textbox(visible=False)

        # TAB 2: Resume Tailor & PDF Generator
        with gr.TabItem("📄 2. Resume Tailoring & PDF"):
            gr.Markdown("### Retrieve your resume and rewrite it to match the job posting.")
            with gr.Row():
                fetch_btn = gr.Button("Fetch Original Resume", variant="secondary")
                tailor_btn = gr.Button("Tailor Resume & Generate PDF", variant="primary")
            
            with gr.Row():
                original_resume_field = gr.Textbox(label="Original Resume", lines=10, interactive=True)
                tailored_resume_field = gr.Textbox(label="Tailored Resume (Generated)", lines=10, interactive=False)
                
            with gr.Row():
                pdf_download = gr.File(label="Download Tailored Resume (PDF)")

        # TAB 3: Cover Letter
        with gr.TabItem("✉️ 3. Cover Letter"):
            gr.Markdown("### Generate a customized cover letter based on your tailored resume.")
            generate_letter_btn = gr.Button("Generate Cover Letter", variant="primary")
            cover_letter_field = gr.Textbox(label="Cover Letter Draft (Editable)", lines=15, interactive=True)

        # TAB 4: Tracker Logs
        with gr.TabItem("📊 4. Sheets Tracker"):
            gr.Markdown("### Review and log this application directly to your Google Sheets spreadsheet.")
            with gr.Row():
                track_date = gr.Textbox(label="Applied Date", value=datetime.now().strftime("%Y-%m-%d"))
                track_company = gr.Textbox(label="Company Name")
                track_role = gr.Textbox(label="Role Title")
            with gr.Row():
                track_status = gr.Textbox(label="Status", value="Applied")
                track_version = gr.Textbox(label="Resume Version", value="Tailored PDF")
                track_deadline = gr.Textbox(label="Last Date to Apply")
            with gr.Row():
                track_summary = gr.Textbox(label="JD Summary / Notes", lines=2)
                
            log_btn = gr.Button("Log to Google Sheets Spreadsheet", variant="primary")
            log_status_field = gr.Textbox(label="Logging Status", interactive=False)

        # TAB 5: Follow-Up
        with gr.TabItem("⏰ 5. Follow-Up Email"):
            gr.Markdown("### Draft a polite follow-up email to be sent after 7 days.")
            generate_followup_btn = gr.Button("Generate Follow-up Email", variant="primary")
            followup_field = gr.Textbox(label="Follow-up Email Draft", lines=10, interactive=False)
            
    # Wire Events
    
    # 1. Analyze Job Description
    analyze_btn.click(
        fn=analyze_job_desc,
        inputs=[jd_input, state_store],
        outputs=[analysis_output, company_field, role_field, deadline_field, summary_field, state_store]
    ).then(
        # Pre-fill tracking textboxes
        fn=lambda c, r, d, s: (c, r, d, s),
        inputs=[company_field, role_field, deadline_field, summary_field],
        outputs=[track_company, track_role, track_deadline, track_summary]
    )
    
    # 2. Fetch Original Resume
    fetch_btn.click(
        fn=load_original_resume,
        inputs=[],
        outputs=[original_resume_field]
    )
    
    # 3. Tailor Resume & Generate PDF
    tailor_btn.click(
        fn=tailor_resume_action,
        inputs=[original_resume_field, state_store],
        outputs=[tailored_resume_field, pdf_download, state_store, track_version]
    )
    
    # 4. Generate Cover Letter
    generate_letter_btn.click(
        fn=gr.helpers.update, # Show loading indicator
        inputs=[],
        outputs=[]
    ).then(
        fn=generate_cover_letter_action,
        inputs=[state_store],
        outputs=[cover_letter_field, state_store]
    )
    
    # 5. Log to Sheets
    log_btn.click(
        fn=log_to_sheets_action,
        inputs=[track_date, track_company, track_role, track_status, track_version, track_deadline, track_summary, state_store],
        outputs=[log_status_field, state_store]
    )
    
    # 6. Follow-up
    generate_followup_btn.click(
        fn=generate_followup_action,
        inputs=[state_store],
        outputs=[followup_field, state_store]
    )

if __name__ == "__main__":
    root_path = os.getenv("ROOT_PATH", None)
    if root_path and not root_path.startswith("/"):
        root_path = "/" + root_path
        
    demo.launch(
        theme=gr.themes.Soft(), 
        css="footer {visibility: hidden}",
        share=True,
        root_path=root_path
    )

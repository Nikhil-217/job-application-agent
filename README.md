# 🎯 Job Application Assistant Agent

![Job Application Assistant Cover Banner](assets/cover_page_banner.png)

> A secure, multi-agent AI system built on Google ADK 2.0 that automates your entire job application workflow — from job analysis and resume tailoring to PDF generation, cover letter writing, Google Drive version backups, and Google Sheets tracking.

**Track:** Concierge Agents (Personal Career Automation & Data Security)  
**Stack:** Google ADK 2.0 · Gemini 3.1 Flash Lite · Google Sheets & Drive APIs · ReportLab · Gradio  
**Cost:** ₹0 — completely free to run on Google free-tier quotas

---

## 🏗️ Architecture

![Architecture Diagram](assets/architecture_diagram.png)

---

## 📋 Prerequisites
- **Python 3.11+**
- Google Account (for Google AI Studio key and Google Drive/Sheets)
- **Gemini API Key**: Obtain a free key from [Google AI Studio](https://aistudio.google.com/apikey)
- Google Cloud Service Account credentials (`service_account.json`) with Sheets and Drive APIs enabled.

---

## 🚀 Quick Start

### 1. Clone & Set Up Directory
```bash
git clone https://github.com/Nikhil-217/job-application-agent.git
cd job-application-agent
```

### 2. Configure Environment Variables
Copy the template and fill in your details:
```bash
cp .env.example .env
```
Open **`.env`** and configure:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
SPREADSHEET_ID=your_google_sheet_id_here
SHEET_NAME=Sheet1
DRIVE_FOLDER_ID=your_shared_google_drive_folder_id_here
RESUME_PATH=./resume.txt
GOOGLE_APPLICATION_CREDENTIALS=./service_account.json
```
*Make sure to place your personal resume in `resume.txt` and your GCP service account credentials in `service_account.json` in the root folder.*

### 3. Automated Install & Run
Run the following make commands to initialize and launch:
```bash
make install          # Creates virtual environment & installs dependencies
python trigger_oauth.py # Run once to log in via browser and generate token.json
make playground       # Starts the Gradio UI at http://localhost:7860
```

---

## 🎮 How to Run

*   **Interactive Playground (Gradio Web UI)**:
    ```bash
    make playground
    ```
    Opens the dashboard at `http://localhost:7860`. Supports document previews, Sheets tracking configuration, and direct PDF downloads.
    
*   **ADK Local Web Server**:
    ```bash
    make run
    ```
    Starts the built-in FastAPI web server for the agent at `http://localhost:8000`.

---

## 🧪 Sample Test Cases

### 1. Job Description Analysis
*   **Input**: Paste a job description for a "Senior Python Developer" at "AlphaTech" requiring FastAPI, PostgreSQL, and Git with a deadline of "2026-07-31" in Tab 1.
*   **Expected**: The Orchestrator routes the input through `security/input_validator.py`, then invokes `job_analysis_agent`. The agent extracts required skills, ATS keywords, company name, and application deadline, saving them in the application state.
*   **Check**: In the Playground UI, the company name ("AlphaTech"), role ("Senior Python Developer"), deadline ("2026-07-31"), and a 1-sentence summary are automatically pre-filled in the text fields on the **Sheets Tracker** tab.

### 2. Resume Tailoring & Google Drive Upload
*   **Input**: Click **Tailor Resume & Generate PDF** in Tab 2.
*   **Expected**: `resume_tailor_agent` is called. It reads `resume.txt` via the Resume MCP server, rewrites experience points to match the JD keywords, runs `generate_resume_pdf` locally, and invokes the `generate_and_upload_resume_pdf` tool. The tool uses `token.json` to upload the PDF directly to the root of your Google Drive folder as `Resume_v1_AlphaTech_Senior_Python_Developer.pdf`.
*   **Check**: In Tab 2, a tailored markdown resume text is displayed, and a downloadable PDF file appears in the file viewer. The version name (e.g. `Resume_v1`) is automatically pre-filled into the "Resume Version" textbox on Tab 4 (Sheets Tracker).

### 3. Google Sheets Tracker Logging
*   **Input**: Navigate to Tab 4 ("Sheets Tracker") and click **Log to Google Sheets**.
*   **Expected**: The Orchestrator calls `tracker_agent`. The agent uses the Sheets MCP server (redirecting status logs to `stderr` to prevent stdio crashes) to write a new row with column values: `Applied Date`, `Company`, `Role`, `Resume Version` (value: `Resume_v1`), `Status` ("Applied"), `Last Date to Apply`, and `JD Description in few words`.
*   **Check**: The UI displays `Logged: AlphaTech - Senior Python Developer on 2026-06-27`. Checking your spreadsheet in real-time shows the new row inserted successfully.

---

## 🛠️ Troubleshooting

### 1. Google Drive 403 Storage Quota Error
*   **Error**: `ERROR: Failed to generate or upload PDF: Google Drive storage quota error...`
*   **Cause**: Service accounts have 0 bytes of default storage quota and cannot upload files directly to personal folders without a user OAuth session.
*   **Fix**: Run `python trigger_oauth.py` once to authenticate your Gmail account. This generates `token.json`, giving the uploader access to your personal 15GB free storage quota.

### 2. Sheets MCP Server stdio Crash (`BrokenResourceError`)
*   **Error**: `ValueError: Tool 'add_rows' not found. Available tools: transfer_to_agent`
*   **Cause**: The standard Google Sheets MCP server prints log messages to `stdout` instead of `stderr`, corrupting the JSON-RPC channel.
*   **Fix**: The project uses **[sheets_server.py](mcp_servers/sheets_server.py)** as a wrapper to redirect all logs to `sys.stderr`. Ensure your `tracker_agent.py` points to this wrapper via `sys.executable`.

### 3. Gemini API Rate Limits (`RESOURCE_EXHAUSTED` / 429)
*   **Error**: `429 Resource Exhausted` or `503 Service Unavailable`
*   **Cause**: Making rapid consecutive calls on the standard free-tier Gemini model.
*   **Fix**: The project configures **`gemini-3.1-flash-lite`** across all agents, which has generous, stable free-tier limits. Check your `.env` to verify your API key is correct.

---

## 📤 GitHub Push Instructions

Ensure your credentials are not uploaded to GitHub. Double-check your ignored files before pushing:

1.  Initialize repository:
    ```bash
    git init
    ```
2.  Check what files are staged (verify that `.env`, `service_account.json`, `credentials.json`, `token.json`, and `resume.txt` are **not** listed):
    ```bash
    git status
    ```
3.  Add files and commit:
    ```bash
    git add .
    git commit -m "Initial commit of Job Application Assistant Agent"
    ```
4.  Add your remote repository and push:
    ```bash
    git remote add origin <your-github-repo-url>
    git branch -M main
    git push -u origin main
    ```

---


## 🎥 Video Walkthrough

You can find the video walkthrough demo here: https://youtu.be/3edDoxGtHYY


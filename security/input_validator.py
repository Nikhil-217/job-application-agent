"""
Input validation and sanitisation for all user inputs.
Runs BEFORE any text reaches the LLM agents.
"""
import re
import time
from typing import Tuple

# Rate limiting state (in-memory, per session)
_request_timestamps = []
RATE_LIMIT_WINDOW = 60   # seconds
RATE_LIMIT_MAX = 10      # max requests per minute

def rate_limit_check() -> Tuple[bool, str]:
    """
    Prevent abuse by limiting to 10 requests per minute.
    Returns (allowed: bool, message: str)
    """
    global _request_timestamps
    now = time.time()
    
    # Remove timestamps older than the window
    _request_timestamps = [t for t in _request_timestamps if now - t < RATE_LIMIT_WINDOW]
    
    if len(_request_timestamps) >= RATE_LIMIT_MAX:
        return False, "Rate limit reached. Please wait a moment before trying again."
    
    _request_timestamps.append(now)
    return True, "OK"


def sanitise_input(text: str) -> Tuple[str, list]:
    """
    Sanitise user input before sending to LLM.
    Returns (clean_text, list_of_warnings)
    """
    warnings = []
    
    # 1. Length check - prevent prompt injection via very long inputs
    MAX_INPUT_LENGTH = 8000
    if len(text) > MAX_INPUT_LENGTH:
        text = text[:MAX_INPUT_LENGTH]
        warnings.append(f"Input truncated to {MAX_INPUT_LENGTH} characters.")
    
    # 2. Detect and neutralise prompt injection attempts
    injection_patterns = [
        r"ignore (previous|above|all) instructions",
        r"you are now",
        r"forget your (instructions|system prompt)",
        r"act as (a |an )?(different|new)",
        r"jailbreak",
        r"DAN mode",
        r"do anything now",
    ]
    for pattern in injection_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            warnings.append("Potential prompt injection detected and neutralised.")
            # Replace the injection attempt with a placeholder
            text = re.sub(pattern, "[FILTERED]", text, flags=re.IGNORECASE)
    
    # 3. Strip HTML/script tags (XSS prevention for web UI)
    text = re.sub(r'<[^>]+>', '', text)
    
    # 4. Normalise whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text, warnings


def detect_pii(text: str) -> list:
    """
    Detect PII patterns in text before logging to external services.
    Returns list of detected PII types (does NOT return the PII itself).
    """
    pii_found = []
    
    patterns = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone_india": r'\b[6-9]\d{9}\b',
        "phone_intl": r'\+?\d[\d\s\-\(\)]{8,14}\d',
        "aadhaar": r'\b\d{4}\s\d{4}\s\d{4}\b',
        "pan_card": r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b',
    }
    
    for pii_type, pattern in patterns.items():
        if re.search(pattern, text):
            pii_found.append(pii_type)
    
    return pii_found


def redact_pii_for_logging(text: str) -> str:
    """
    Redact PII before sending to external services like Google Sheets.
    Replaces PII with [REDACTED-TYPE] placeholders.
    Only the tracker agent uses this — cover letters stay intact for the user.
    """
    redactions = {
        "email": (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED-EMAIL]'),
        "phone": (r'\b[6-9]\d{9}\b', '[REDACTED-PHONE]'),
        "aadhaar": (r'\b\d{4}\s\d{4}\s\d{4}\b', '[REDACTED-AADHAAR]'),
    }
    
    for _, (pattern, replacement) in redactions.items():
        text = re.sub(pattern, replacement, text)
    
    return text


def validate_job_description(text: str) -> Tuple[bool, str]:
    """
    Check if the input looks like a real job description.
    Prevents misuse (e.g. asking the agent to do unrelated tasks).
    """
    # Must have some minimum length
    if len(text.strip()) < 100:
        return False, "Input too short to be a job description. Please paste the full JD."
    
    # Should contain at least some job-related keywords
    jd_keywords = [
        "experience", "skills", "responsibilities", "requirements",
        "role", "position", "salary", "apply", "team", "work",
        "qualification", "bachelor", "degree", "years"
    ]
    
    text_lower = text.lower()
    matches = sum(1 for kw in jd_keywords if kw in text_lower)
    
    if matches < 3:
        return False, "This doesn't look like a job description. Please paste the full job posting text."
    
    return True, "Valid job description"

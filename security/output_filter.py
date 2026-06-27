"""
Filter agent outputs before displaying to user or logging externally.
"""

def filter_output(text: str, destination: str = "user") -> str:
    """
    destination: "user" | "sheets" | "log"
    """
    if destination == "sheets":
        # Redact PII before logging to Google Sheets
        from security.input_validator import redact_pii_for_logging
        text = redact_pii_for_logging(text)
        # Truncate notes field for Sheets
        text = text[:200] if len(text) > 200 else text
    
    # Remove any accidentally leaked environment variable patterns
    import re
    text = re.sub(r'[A-Z_]{3,}=[^\s]+', '[ENV_VAR_REDACTED]', text)
    
    # Remove anything that looks like a file path with credentials
    text = re.sub(r'(service_account|credentials|\.env)[^\s]*', '[PATH_REDACTED]', text)
    
    return text

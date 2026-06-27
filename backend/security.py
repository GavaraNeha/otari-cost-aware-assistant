import re

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "system prompt",
    "jailbreak",
    "forget instructions",
    "you are now",
    "act as",
    "pretend you are",
    "disregard",
    "override",
    "bypass",
    "dan mode",
    "developer mode",
    "sudo mode",
    "admin mode",
    "unlock",
    "no restrictions",
    "without restrictions",
    "ignore ethics",
    "ignore safety",
]

def detect_injection(prompt: str):
    prompt_lower = prompt.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in prompt_lower:
            return {
                "is_threat": True,
                "risk_score": 90,
                "reason": f"Detected: '{pattern}'",
                "action": "BLOCKED"
            }
    return {
        "is_threat": False,
        "risk_score": 0,
        "reason": "Clean",
        "action": "ALLOWED"
    }


def mask_sensitive_data(prompt: str):
    masked = prompt
    flags = []

    # Mask emails
    if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', masked):
        masked = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                        '[EMAIL MASKED]', masked)
        flags.append("email")

    # Mask phone numbers
    if re.search(r'\b\d{10}\b|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b', masked):
        masked = re.sub(r'\b\d{10}\b|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b',
                        '[PHONE MASKED]', masked)
        flags.append("phone")

    # Mask API keys
    if re.search(r'\bsk[-_][a-zA-Z0-9]{10,}\b', masked):
        masked = re.sub(r'\bsk[-_][a-zA-Z0-9]{10,}\b',
                        '[API KEY MASKED]', masked)
        flags.append("api_key")

    # Mask credit cards
    if re.search(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', masked):
        masked = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
                        '[CARD MASKED]', masked)
        flags.append("credit_card")

    # Mask passwords
    if re.search(r'password\s*[:=]\s*\S+', masked, re.IGNORECASE):
        masked = re.sub(r'(password\s*[:=]\s*)\S+',
                        r'\1[PASSWORD MASKED]', masked, flags=re.IGNORECASE)
        flags.append("password")

    # Mask Aadhaar numbers (Indian ID)
    if re.search(r'\b\d{4}\s\d{4}\s\d{4}\b', masked):
        masked = re.sub(r'\b\d{4}\s\d{4}\s\d{4}\b',
                        '[AADHAAR MASKED]', masked)
        flags.append("aadhaar")

    return {
        "masked_prompt": masked,
        "was_masked": len(flags) > 0,
        "masked_types": flags
    }
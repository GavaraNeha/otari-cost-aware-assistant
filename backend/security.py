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
]

def detect_injection(prompt: str):
    prompt_lower = prompt.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in prompt_lower:
            risk_score = 90
            return {
                "is_threat": True,
                "risk_score": risk_score,
                "reason": f"Detected: '{pattern}'",
                "action": "BLOCKED"
            }
    return {
        "is_threat": False,
        "risk_score": 0,
        "reason": "Clean",
        "action": "ALLOWED"
    }
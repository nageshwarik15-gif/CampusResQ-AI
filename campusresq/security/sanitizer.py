"""
Input Sanitization & Prompt Injection Defenses
Conforms strictly to IEEE 1016-2009 SDD §9.1 and SRS §6.2.
Scans and scrubs ingested 911 transcripts, plain text alerts, and environmental injects
to prevent indirect prompt injection, jailbreaks, and instructions that compromise life safety.
"""

import re
from typing import Tuple, Optional, Any, Dict
from ..models.schemas import IncidentTelemetryPayload

# Regex patterns matching indirect prompt injection & adversarial jailbreak attempts
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directives|rules|prompts)",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|directives|rules|prompts)",
    r"forget\s+(all\s+)?(previous|prior|above)\s+(instructions|context|rules)",
    r"override\s+(all\s+)?(safety|system|protocols|guidelines|guardrails)",
    r"bypass\s+(all\s+)?(safety|hitl|gating|protocols|rules)",
    r"you\s+are\s+now\s+(an?\s+)?(unrestricted|jailbroken|evil|dan|developer\s+mode)",
    r"system\s*:\s*you\s+must",
    r"<\s*script[^>]*>",
    r"javascript\s*:",
    r"assistant\s*:\s*",
    r"\[system\s+directive\]",
    r"do\s+not\s+(evacuate|call\s+911|alert|lockdown)\s+anyone",
    r"tell\s+everyone\s+to\s+stay\s+in\s+the\s+burning\s+building"
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

class PromptInjectionDetected(Exception):
    """Raised when an active prompt injection attack is detected in strict mode."""
    pass

def detect_prompt_injection(text: str) -> Tuple[bool, Optional[str]]:
    """
    Scans a string against compiled adversarial injection patterns.
    Returns (True, matching_pattern) if detected, otherwise (False, None).
    """
    if not text or not isinstance(text, str):
        return False, None

    for pattern in COMPILED_PATTERNS:
        match = pattern.search(text)
        if match:
            return True, match.group(0)

    return False, None

def sanitize_text(text: str, redact: bool = True) -> str:
    """
    Cleanses input text by scrubbing detected prompt injection vectors
    and stripping dangerous control/script sequences.
    """
    if not text or not isinstance(text, str):
        return ""

    sanitized = text

    # Strip HTML / Script tags
    sanitized = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", sanitized, flags=re.IGNORECASE | re.DOTALL)
    sanitized = re.sub(r"<\s*[^>]+>", "", sanitized)

    # Scrub injection patterns
    for pattern in COMPILED_PATTERNS:
        if pattern.search(sanitized):
            if redact:
                sanitized = pattern.sub("[SUSPICIOUS_DIRECTIVE_REDACTED]", sanitized)

    return sanitized.strip()

def sanitize_telemetry_payload(payload: IncidentTelemetryPayload) -> IncidentTelemetryPayload:
    """
    Sanitizes all text fields within an IncidentTelemetryPayload before it enters
    the LangGraph cognitive multi-agent pipeline.
    """
    if not payload.raw_data:
        return payload

    cleaned_raw_data = dict(payload.raw_data)

    # Sanitize 911 caller transcript if present
    if "transcript_text" in cleaned_raw_data:
        original = str(cleaned_raw_data["transcript_text"])
        cleaned_raw_data["transcript_text"] = sanitize_text(original)

    # Sanitize notes or description
    if "notes" in cleaned_raw_data:
        cleaned_raw_data["notes"] = sanitize_text(str(cleaned_raw_data["notes"]))

    if "description" in cleaned_raw_data:
        cleaned_raw_data["description"] = sanitize_text(str(cleaned_raw_data["description"]))

    # Sanitize hazard indicator strings
    if "hazard_indicators" in cleaned_raw_data and isinstance(cleaned_raw_data["hazard_indicators"], list):
        cleaned_raw_data["hazard_indicators"] = [
            sanitize_text(str(ind)) for ind in cleaned_raw_data["hazard_indicators"]
        ]

    payload.raw_data = cleaned_raw_data
    return payload

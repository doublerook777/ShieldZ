"""Allowlist firewall and PII output guard for LLM explanations (Invariant I2).

Functions:
    - validate_prompt: Enforces that prompts match the fixed template byte-for-byte
      and contain zero digits before sending to the model.
    - validate_output: Inspects LLM output and rejects PII-shaped content (runs of 4+ digits,
      currency amounts, phone patterns, URLs, @).
"""

from __future__ import annotations

import re

from shieldz.contracts import ExplainJob
from shieldz.explainer.prompt import build_prompt

# Regexes for output guard
_RE_4_OR_MORE_DIGITS = re.compile(r"\d{4,}")
_RE_CURRENCY = re.compile(r"(?:₹|rs\.?|inr)\s*\d+|\d+\s*(?:₹|rs\.?|inr|rupees?)", re.IGNORECASE)
_RE_PHONE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")
_RE_URL = re.compile(r"(?:https?://|www\.)[^\s/$.?#].[^\s]*", re.IGNORECASE)


def validate_prompt(prompt: str, job: ExplainJob) -> tuple[bool, str]:
    """Validate prompt before sending to LLM.

    Requires:
        1. Length within bounds (<= 2000 chars).
        2. Zero digits anywhere in the prompt (Invariant I2).
        3. Byte-for-byte exact match with independently rendered template.

    Returns:
        (is_valid, reason)
    """
    if len(prompt) > 2000:
        return False, "Prompt exceeds maximum length (2000 chars)"

    if any(c.isdigit() for c in prompt):
        return False, "Prompt contains digits violating Invariant I2"

    try:
        expected = build_prompt(job)
    except Exception as exc:
        return False, f"Failed to render reference prompt: {exc}"

    if prompt != expected:
        return False, "Prompt does not match expected canonical template"

    return True, "OK"


def validate_output(text: str) -> tuple[bool, str]:
    """Validate generated explanation text before storing or displaying.

    Rejects PII-shaped content:
        1. Any run of 4+ digits (accounts, OTPs, long numbers).
        2. Currency amounts (₹, Rs, INR next to numbers).
        3. Phone number patterns.
        4. URLs (http://, https://, www.).
        5. Email addresses or '@' symbols.

    Small benign numbers (e.g. "24 hours", "3 steps", "2 minutes") are permitted.

    Returns:
        (is_valid, reason)
    """
    cleaned = text.strip()
    if len(cleaned) < 10:
        return False, "Output too short (< 10 chars)"
    if len(cleaned) > 1500:
        return False, "Output exceeds maximum length (1500 chars)"

    # 1. 4+ consecutive digits
    if _RE_4_OR_MORE_DIGITS.search(cleaned):
        return False, "Output contains run of 4 or more digits"

    # 2. Currency amounts
    if _RE_CURRENCY.search(cleaned):
        return False, "Output contains currency amounts"

    # 3. Phone patterns: check regex or 7+ separated digits
    if _RE_PHONE.search(cleaned):
        return False, "Output contains phone number pattern"

    # Scan for 7+ digits grouped by spaces/hyphens
    grouped_digits_match = re.search(r"\b\d(?:[\s-]*\d){6,}\b", cleaned)
    if grouped_digits_match:
        return False, "Output contains phone/account digit pattern"

    # 4. URLs
    if _RE_URL.search(cleaned):
        return False, "Output contains URL"

    # 5. Email / @
    if "@" in cleaned:
        return False, "Output contains @ symbol or email address"

    return True, "OK"

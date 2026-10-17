"""Prompt builder for Granite Explainer.

Constructs prompts strictly from :class:`~shieldz.contracts.ExplainJob`
using fixed templates and closed enums (DecisionKind, Level, ReasonCode, Language).
No free text, account IDs, names, memos, or amounts can enter the prompt by construction.
Enforces Invariant I2: the rendered prompt contains zero digits.
"""

from __future__ import annotations

from shieldz.contracts import ExplainJob, Language, ReasonCode

REASON_DESCRIPTIONS: dict[ReasonCode, str] = {
    ReasonCode.AMOUNT_HIGH_VS_BALANCE: "The payment uses most of the money in the account.",
    ReasonCode.ACCOUNT_DRAIN: "The payment would leave the account empty.",
    ReasonCode.NEW_RECIPIENT: "The receiving account is new or rarely used.",
    ReasonCode.RISKY_TRANSFER_TYPE: "This kind of transfer is often used in scams.",
    ReasonCode.MULE_ACCOUNT_PATTERN: (
        "The receiving account looks like one used to pass on stolen money."
    ),
    ReasonCode.LARGE_AMOUNT: "The amount is unusually large.",
    ReasonCode.UNUSUAL_TIME: "The payment is at an unusual time.",
    ReasonCode.OTHER_PATTERN: "Something else about the payment looks unusual.",
}

LANGUAGE_NAMES: dict[Language, str] = {
    Language.EN: "English",
    Language.HI: "Hindi",
    Language.TA: "Tamil",
}

PROMPT_FOOTER: str = (
    "Write two or three calm, simple sentences warning an elderly customer. "
    "Suggest they pause and call their bank on the number printed on their card. "
    "Do not mention any numbers, names or links."
)


def build_prompt(job: ExplainJob) -> str:
    """Render the canonical LLM prompt from an ExplainJob.

    The output format is strictly deterministic:
        Decision: <DECISION>. Risk: <RISK>.
        Reasons:
        - <CODE> (<LEVEL>): <DESCRIPTION>
        Language: <LANGUAGE>.
        <PROMPT_FOOTER>

    Guarantees:
        - Zero digits in output (Invariant I2).
        - No request-specific free text.
    """
    reasons_list = job.reasons
    if not reasons_list:
        desc = REASON_DESCRIPTIONS[ReasonCode.OTHER_PATTERN]
        reasons_text = f"- {ReasonCode.OTHER_PATTERN.value} ({job.risk_level.value}): {desc}"
    else:
        lines: list[str] = []
        for r in reasons_list:
            code_enum = r.code if isinstance(r.code, ReasonCode) else ReasonCode(r.code)
            level_val = r.level.value if hasattr(r.level, "value") else str(r.level)
            desc = REASON_DESCRIPTIONS.get(code_enum, REASON_DESCRIPTIONS[ReasonCode.OTHER_PATTERN])
            lines.append(f"- {code_enum.value} ({level_val}): {desc}")
        reasons_text = "\n".join(lines)

    lang_enum = job.language if isinstance(job.language, Language) else Language(job.language)
    lang_name = LANGUAGE_NAMES.get(lang_enum, "English")
    dec_val = job.decision.value if hasattr(job.decision, "value") else str(job.decision)
    risk_val = job.risk_level.value if hasattr(job.risk_level, "value") else str(job.risk_level)

    prompt = (
        f"Decision: {dec_val}. Risk: {risk_val}.\n"
        f"Reasons:\n"
        f"{reasons_text}\n"
        f"Language: {lang_name}.\n"
        f"{PROMPT_FOOTER}"
    )

    # Sanity check: must contain no digits
    if any(c.isdigit() for c in prompt):
        raise ValueError("Prompt construction generated digits violating Invariant I2")

    return prompt

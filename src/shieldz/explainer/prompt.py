"""Prompt builder for Granite Explainer.

Constructs prompts strictly from :class:`~shieldz.contracts.ExplainJob`
using fixed templates and closed enums (DecisionKind, Level, ReasonCode, Language).
No free text, account IDs, names, memos, or amounts can enter the prompt by construction.
Enforces Invariant I2: the rendered prompt contains zero digits.
"""

from __future__ import annotations

from shieldz.contracts import ExplainJob, Language, ReasonCode
from shieldz.explainer.template import TemplateExplainer

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

# A 350M *base* model cannot compose a warning from a list of codes: measured on the VM it either
# repeated "Do not mention ..." until the tokens ran out or stated falsehoods ("your account has
# been drained"). It can rewrite text, so the prompt gives it the human-reviewed English template
# sentence and asks for simpler words. The two examples are fixed text. Everything in the prompt
# still comes from enums and constants, with no digits and no request data (I2).
PROMPT_HEAD: str = (
    "Rewrite each bank warning in short, simple, calm words for an elderly customer.\n\n"
)
PROMPT_EXAMPLES: str = (
    "Warning: The requested amount is unusually large compared to your normal activity. "
    "This payment is occurring at an unusual hour. Please pause and verify this transfer by "
    "calling your bank on the official number on your card before proceeding.\n"
    "Simple words: This is a very big payment, and it is late at night, which is not like you. "
    "Please stop for a moment and call your bank on the number on your card.\n\n"
    "Warning: This payment uses most of the funds in your account. This transfer method is "
    "commonly targeted by urgent payment scams. Please pause and verify this transfer by calling "
    "your bank on the official number on your card before proceeding.\n"
    "Simple words: This payment would use up most of your money, and scammers often ask for "
    "payments like this. Please wait and call your bank on the number on your card.\n\n"
)


def build_prompt(job: ExplainJob) -> str:
    """Render the canonical LLM prompt from an ExplainJob.

        <PROMPT_HEAD><PROMPT_EXAMPLES>Warning: <English template text for the job's reason codes>
        Simple words:

    The model completes the last line. The prompt always uses the English template, so only
    English jobs are sent to the LLM (the worker keeps Hindi and Tamil on the reviewed templates).

    Guarantees:
        - Zero digits in output (Invariant I2).
        - No request-specific free text: the only variable part is the template sentence chosen by
          the reason-code enum values.
    """
    english = job.model_copy(update={"language": Language.EN})
    warning = TemplateExplainer().explain(english).text
    prompt = f"{PROMPT_HEAD}{PROMPT_EXAMPLES}Warning: {warning}\nSimple words:"

    # Sanity check: must contain no digits
    if any(c.isdigit() for c in prompt):
        raise ValueError("Prompt construction generated digits violating Invariant I2")

    return prompt

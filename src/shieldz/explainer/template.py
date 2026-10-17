"""Deterministic template-based explanations for ShieldZ.

Used locally during development and as the bulletproof production fallback
when the Granite LLM is busy, unavailable, or rejected by the output guard.
Provides human-written, reviewed warnings in English, Hindi, and Tamil.
"""

from __future__ import annotations

from shieldz.clock import now_utc
from shieldz.contracts import (
    ExplainJob,
    Explanation,
    ExplanationSource,
    Language,
    ReasonCode,
)

TEMPLATES_EN: dict[ReasonCode, str] = {
    ReasonCode.AMOUNT_HIGH_VS_BALANCE: "This payment uses most of the funds in your account.",
    ReasonCode.ACCOUNT_DRAIN: "This payment would completely drain your remaining balance.",
    ReasonCode.NEW_RECIPIENT: (
        "The receiving account is new and has not received transfers before."
    ),
    ReasonCode.RISKY_TRANSFER_TYPE: (
        "This transfer method is commonly targeted by urgent payment scams."
    ),
    ReasonCode.MULE_ACCOUNT_PATTERN: (
        "The destination account matches characteristics of an unauthorized relay account."
    ),
    ReasonCode.LARGE_AMOUNT: (
        "The requested amount is unusually large compared to your normal activity."
    ),
    ReasonCode.UNUSUAL_TIME: "This payment is occurring at an unusual hour.",
    ReasonCode.OTHER_PATTERN: "Unusual transaction indicators were detected for this transfer.",
}

FOOTER_EN = (
    "Please pause and verify this transfer by calling your bank on the official "
    "number on your card before proceeding."
)

TEMPLATES_HI: dict[ReasonCode, str] = {
    ReasonCode.AMOUNT_HIGH_VS_BALANCE: "यह भुगतान आपके खाते के अधिकांश पैसों का उपयोग करता है।",
    ReasonCode.ACCOUNT_DRAIN: "यह भुगतान आपके खाते का शेष बैलेंस पूरी तरह से खाली कर देगा।",
    ReasonCode.NEW_RECIPIENT: "प्राप्तकर्ता का खाता नया है और इससे पहले लेनदेन नहीं हुआ है।",
    ReasonCode.RISKY_TRANSFER_TYPE: "इस प्रकार के ट्रांसफर का उपयोग अक्सर धोखाधड़ी में किया जाता है।",
    ReasonCode.MULE_ACCOUNT_PATTERN: "प्राप्तकर्ता का खाता संदिग्ध लेनदेन जैसा दिखाई देता है।",
    ReasonCode.LARGE_AMOUNT: "यह राशि आपकी सामान्य गतिविधि से काफी अधिक है।",
    ReasonCode.UNUSUAL_TIME: "यह भुगतान असामान्य समय पर किया जा रहा है।",
    ReasonCode.OTHER_PATTERN: "इस लेनदेन में असामान्य गतिविधि देखी गई है।",
}

FOOTER_HI = "कृपया रुकें और आगे बढ़ने से पहले अपने डेबिट कार्ड पर लिखे बैंक के आधिकारिक नंबर पर कॉल करके पुष्टि करें।"

TEMPLATES_TA: dict[ReasonCode, str] = {
    ReasonCode.AMOUNT_HIGH_VS_BALANCE: (
        "இந்த பரிவர்த்தனை உங்கள் கணக்கில் உள்ள பெரும்பாலான பணத்தைப் பயன்படுத்துகிறது."
    ),
    ReasonCode.ACCOUNT_DRAIN: ("இந்த பரிவர்த்தனை உங்கள் கணக்கு இருப்பை முழுமையாகக் காலி செய்துவிடும்."),
    ReasonCode.NEW_RECIPIENT: ("பெறுநரின் கணக்கு புதியது மற்றும் இதற்கு முன் பரிவர்த்தனைகள் செய்யப்படவில்லை."),
    ReasonCode.RISKY_TRANSFER_TYPE: ("இந்த வகையான பரிவர்த்தனை பெரும்பாலும் மோசடிகளில் பயன்படுத்தப்படுகிறது."),
    ReasonCode.MULE_ACCOUNT_PATTERN: ("பெறும் கணக்கு சந்தேகத்திற்குரிய செயல்பாட்டைக் காட்டுகிறது."),
    ReasonCode.LARGE_AMOUNT: ("கோரப்பட்ட தொகை உங்கள் வழக்கமான செயல்பாட்டை விட அதிகமாக உள்ளது."),
    ReasonCode.UNUSUAL_TIME: "இந்த பரிவர்த்தனை வழக்கத்திற்கு மாறான நேரத்தில் நடைபெறுகிறது.",
    ReasonCode.OTHER_PATTERN: ("இந்த பரிவர்த்தனையில் வழக்கத்திற்கு மாறான அம்சங்கள் கண்டறியப்பட்டுள்ளன."),
}

FOOTER_TA = (
    "தயவுசெய்து பரிவர்த்தனையை நிறுத்தி, உங்கள் வங்கி அட்டையில் உள்ள அதிகாரப்பூர்வ "
    "எண்ணில் தொடர்பு கொண்டு உறுதிப்படுத்தவும்."
)

TEMPLATES_BY_LANG: dict[Language, tuple[dict[ReasonCode, str], str]] = {
    Language.EN: (TEMPLATES_EN, FOOTER_EN),
    Language.HI: (TEMPLATES_HI, FOOTER_HI),
    Language.TA: (TEMPLATES_TA, FOOTER_TA),
}


class TemplateExplainer:
    """Deterministic, rule-based explanation generator."""

    def explain(self, job: ExplainJob) -> Explanation:
        """Generate human-reviewed warning text for the job's reason codes."""
        lang = job.language if isinstance(job.language, Language) else Language(job.language)
        templates, footer = TEMPLATES_BY_LANG.get(lang, (TEMPLATES_EN, FOOTER_EN))

        sentences: list[str] = []
        if not job.reasons:
            sentences.append(templates[ReasonCode.OTHER_PATTERN])
        else:
            for r in job.reasons:
                code_enum = r.code if isinstance(r.code, ReasonCode) else ReasonCode(r.code)
                sentence = templates.get(code_enum, templates[ReasonCode.OTHER_PATTERN])
                if sentence not in sentences:
                    sentences.append(sentence)

        body = " ".join(sentences)
        full_text = f"{body} {footer}"

        return Explanation(
            decision_id=job.decision_id,
            text=full_text,
            source=ExplanationSource.TEMPLATE,
            language=lang,
            ts=now_utc(),
        )

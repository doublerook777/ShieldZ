"""The one place personal data is touched (invariant I1).

`strip` is the only code that reads a `PaymentRequest`'s personal fields. The route handler and
`Pipeline.handle` hold the object but only pass it on, and `test_only_strip_reads_personal_fields`
enforces this. Names, phone, memo and family contact are dropped. Account ids become keyed HMAC
tokens. Amount and balances stay as numbers because the feature step needs them; `engineer()`
turns them into ratios and they go no further than memory.
"""

from __future__ import annotations

from shieldz.contracts import FeatureInput, PaymentRequest
from shieldz.privacy.tokenize import Tokenizer, default_tokenizer


def strip(request: PaymentRequest, tokenizer: Tokenizer | None = None) -> FeatureInput:
    tokenizer = tokenizer or default_tokenizer()
    return FeatureInput(
        tx_type=request.tx_type,
        amount=request.amount,
        payer_balance_before=request.payer_balance_before,
        payee_balance_before=request.payee_balance_before,
        payee_is_merchant=request.payee_is_merchant,
        hour_of_day=request.timestamp.hour,
        payee_token=tokenizer.token(request.payee_account),
        payer_token=tokenizer.token(request.payer_account),
        language=request.language,
    )

"""Canary record generation for ShieldZ Leak Audit.

Generates deterministic, unique fake identities (Indian locale) that are replayed
through the platform to detect any leakage into logs, databases, prompts, or files.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from faker import Faker


@dataclass(frozen=True)
class CanaryRecord:
    """A single synthetic canary identity with distinctive PII fields."""

    canary_id: str
    payer_name: str
    payer_phone: str
    payer_account: str
    payee_name: str
    payee_account: str
    upi_id: str
    email: str
    memo: str
    amount: float
    payer_balance_before: float

    def get_sensitive_strings(self) -> set[str]:
        """Returns the set of raw sensitive strings that must never leak."""
        return {
            self.payer_name,
            self.payer_phone,
            self.payer_account,
            self.payee_name,
            self.payee_account,
            self.upi_id,
            self.email,
            self.memo,
            f"{self.amount:.2f}",
        }

    def to_payment_request_dict(self) -> dict[str, Any]:
        """Converts canary to a dictionary matching the PaymentRequest contract."""
        return {
            "request_id": self.canary_id,
            "payer_name": self.payer_name,
            "payer_phone": self.payer_phone,
            "payer_account": self.payer_account,
            "payee_name": self.payee_name,
            "payee_account": self.payee_account,
            "upi_id": self.upi_id,
            "email": self.email,
            "memo": self.memo,
            "amount": self.amount,
            "payer_balance_before": self.payer_balance_before,
            "tx_type": "TRANSFER",
        }


def _generate_distinctive_amount(rng: random.Random) -> float:
    """Generates an amount with distinctive non-zero paise (e.g. .37, .83)."""
    whole = rng.randint(500, 95000)
    # Pick distinctive paise (never .00, .50, etc.)
    paise = rng.choice([13, 17, 23, 29, 31, 37, 41, 43, 47, 53, 59, 67, 71, 73, 79, 83, 89, 97])
    return float(Decimal(f"{whole}.{paise:02d}"))


def generate_canaries(n: int = 1000, seed: int = 42) -> list[CanaryRecord]:
    """Generates `n` deterministic canary records with Indian locale details.

    Args:
        n: Number of canary records to generate.
        seed: Random seed for exact reproducibility across runs.

    Returns:
        List of CanaryRecord objects.
    """
    fake = Faker("en_IN")
    fake.seed_instance(seed)
    rng = random.Random(seed)

    canaries: list[CanaryRecord] = []
    for i in range(1, n + 1):
        canary_hex = f"{rng.getrandbits(32):08x}"
        canary_id = f"CANARY-{i:04d}-{canary_hex}"

        first_name = fake.first_name()
        last_name = fake.last_name()
        payer_name = f"{first_name} {last_name}"

        payee_first = fake.first_name()
        payee_last = fake.last_name()
        payee_name = f"{payee_first} {payee_last}"

        # 10-digit Indian mobile number
        mobile_digits = f"{rng.randint(7000000000, 9999999999)}"
        payer_phone = f"+91 {mobile_digits[:5]} {mobile_digits[5:]}"

        # 12-digit bank accounts
        payer_acc = f"{rng.randint(100000000000, 999999999999)}"
        payee_acc = f"{rng.randint(100000000000, 999999999999)}"

        clean_user = f"{first_name.lower()}.{last_name.lower()}{i}"
        upi_bank = rng.choice(["okaxis", "okhdfcbank", "oksbi", "icici", "paytm"])
        upi_id = f"{clean_user}@{upi_bank}"
        email = f"{clean_user}@{fake.free_email_domain()}"

        memo = f"CANARY-{canary_hex}-URGENT"
        amount = _generate_distinctive_amount(rng)
        payer_balance_before = float(Decimal(f"{amount + rng.randint(50, 5000):.2f}"))

        canaries.append(
            CanaryRecord(
                canary_id=canary_id,
                payer_name=payer_name,
                payer_phone=payer_phone,
                payer_account=payer_acc,
                payee_name=payee_name,
                payee_account=payee_acc,
                upi_id=upi_id,
                email=email,
                memo=memo,
                amount=amount,
                payer_balance_before=payer_balance_before,
            )
        )

    return canaries


def generate_decoys(n: int = 1000, seed: int = 999) -> list[CanaryRecord]:
    """Generates `n` decoy canaries for the Negative Control.

    These are NEVER sent through the system. A valid Leak Audit must detect
    0 hits for decoys, proving no false positives on unrelated data.
    """
    return generate_canaries(n=n, seed=seed)

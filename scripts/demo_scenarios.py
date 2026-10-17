#!/usr/bin/env python3
"""ShieldZ — Demo Scenarios (M7 / M8).

Three scripted stories telling the end-to-end story of ShieldZ:
  (a) "Digital Arrest" scam: Coercive fake-police video call ordering Mrs. Savitri Devi
      to drain her life savings (₹4,85,000 of ₹4,90,000) to an unverified "escrow" -> BLOCK.
  (b) Routine Utility Bill payment: Monthly ₹1,840.50 electricity payment to a seeded
      merchant (DEMO-ELECTRICITY-BOARD) -> ALLOW.
  (c) Borderline Emergency: ₹8,500 clinic payment while traveling to a newly encountered
      provider, leaving savings intact -> REVIEW.

Usage:
    python scripts/demo_scenarios.py --list
    python scripts/demo_scenarios.py --show digital_arrest
    python scripts/demo_scenarios.py --json
    python scripts/demo_scenarios.py --verify
    python scripts/demo_scenarios.py --run [--url http://localhost:8000]
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from shieldz.contracts import (
    DecisionKind,
    Language,
    Level,
    PaymentRequest,
    ReasonCode,
    TxType,
)


@dataclass(frozen=True)
class DemoScenario:
    """A complete scripted demo story."""

    id: str
    title: str
    category: str
    victim_profile: str
    storyline: str
    payment: dict[str, Any]
    expected_decision: DecisionKind
    expected_risk: Level
    expected_reasons: list[ReasonCode]
    granite_prompt_preview: str
    family_alert_preview: str

    def to_payment_request(self) -> PaymentRequest:
        """Instantiates and validates the Pydantic PaymentRequest contract."""
        data = dict(self.payment)
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return PaymentRequest(**data)


SEEDED_PAYEE = "DEMO-ELECTRICITY-BOARD"  # history seed: 5,000+ prior payments

SCENARIOS: dict[str, DemoScenario] = {
    "digital_arrest": DemoScenario(
        id="digital_arrest",
        title="Scenario A: 'Digital Arrest' Imposter Scam",
        category="High-Risk Coercion Scam",
        victim_profile=(
            "Mrs. Savitri Devi Kulkarni, 72-year-old retired schoolteacher living in Pune."
        ),
        storyline=(
            "Mrs. Kulkarni receives a Skype video call from an imposter in a fake police uniform "
            "posing as a senior CBI investigator. He claims an illegal parcel containing "
            "narcotics and counterfeit passports was seized at Mumbai airport. Under threat "
            "of immediate 'Digital Arrest' and public disgrace, he coerces her into liquidating "
            "her fixed deposits and transferring ₹4,85,000—her entire account balance "
            "(₹4,85,000)—into a fraudulent 'Supreme Court Asset Verification Escrow' account "
            "at 2:45 AM. She is told the funds will be 'verified and returned in 1 hour'."
        ),
        payment={
            "payer_name": "Savitri Devi Kulkarni",
            "payer_phone": "+91 98201 44521",
            "payer_account": "ACC-9041-3321-7788",
            "payee_name": "Supreme Court Clearance Escrow",
            "payee_account": "UPI-cbi.clearance.escrow99@okaxis",
            "memo": "URGENT SUPREME COURT VERIFICATION ESCROW DEPOSIT",
            "family_contact": "+91 98201 99882 (Son: Anand Kulkarni)",
            "tx_type": TxType.TRANSFER.value,
            "amount": 485000.00,
            "payer_balance_before": 485000.00,
            "payee_balance_before": 0.0,
            "payee_is_merchant": False,
            "timestamp": "2026-10-17T02:45:00+05:30",
            "language": Language.EN.value,
        },
        expected_decision=DecisionKind.BLOCK,
        expected_risk=Level.HIGH,
        expected_reasons=[
            ReasonCode.AMOUNT_HIGH_VS_BALANCE,
            ReasonCode.MULE_ACCOUNT_PATTERN,
            ReasonCode.ACCOUNT_DRAIN,
        ],
        granite_prompt_preview=(
            "Decision: BLOCK. Risk: HIGH.\n"
            "Reasons:\n"
            "- AMOUNT_HIGH_VS_BALANCE (HIGH): The payment uses most of the money in the account.\n"
            "- MULE_ACCOUNT_PATTERN (HIGH): The receiving account has mule or suspicious "
            "characteristics.\n"
            "- ACCOUNT_DRAIN (HIGH): The payment would leave the account empty.\n"
            "Language: English.\n"
            "Write two or three calm, simple sentences warning an elderly customer. "
            "Suggest they pause and call their bank on the number printed on their card. "
            "Do not mention any numbers, names or links."
        ),
        family_alert_preview=(
            "🛡️ [ShieldZ Guardian Alert] A high-risk payment of ₹4,85,000 from Savitri Devi "
            "Kulkarni was safely paused. Triggers: Account drain to an unverified recipient at "
            "2:45 AM. Please call your mother immediately. Common scam tactic detected."
        ),
    ),
    "utility_bill": DemoScenario(
        id="utility_bill",
        title="Scenario B: Routine Monthly Electricity Bill",
        category="Legitimate Recurring Payment",
        victim_profile="Mrs. Savitri Devi Kulkarni, paying her monthly household expenses.",
        storyline=(
            "On Saturday morning at 11:15 AM, Mrs. Kulkarni logs in to pay her regular monthly "
            "electricity bill of ₹1,840.50 to Maharashtra State Electricity Distribution Co. "
            "Ltd. (MSEDCL). The payee account (DEMO-ELECTRICITY-BOARD) is a verified utility "
            "merchant with over 5,000 successful historical payments in the platform seed "
            "history. The amount represents less than 0.4% of her available balance."
        ),
        payment={
            "payer_name": "Savitri Devi Kulkarni",
            "payer_phone": "+91 98201 44521",
            "payer_account": "ACC-9041-3321-7788",
            "payee_name": "State Electricity Distribution Corp Ltd",
            "payee_account": "DEMO-ELECTRICITY-BOARD",
            "memo": "Electricity bill payment consumer no 44019281",
            "family_contact": "+91 98201 99882 (Son: Anand Kulkarni)",
            "tx_type": TxType.PAYMENT.value,
            "amount": 1840.50,
            "payer_balance_before": 490000.00,
            "payee_balance_before": 1540000.00,
            "payee_is_merchant": True,
            "timestamp": "2026-10-17T11:15:00+05:30",
            "language": Language.EN.value,
        },
        expected_decision=DecisionKind.ALLOW,
        expected_risk=Level.LOW,
        expected_reasons=[],
        granite_prompt_preview="[No explanation required: Transaction instantly allowed]",
        family_alert_preview="[No alert required: Normal transaction]",
    ),
    "borderline_clinic": DemoScenario(
        id="borderline_clinic",
        title="Scenario C: Urgent Diagnostic Clinic Payment While Traveling",
        category="Borderline / Cautionary Transaction",
        victim_profile=("Mrs. Savitri Devi Kulkarni, traveling to Nagpur for a family event."),
        storyline=(
            "While visiting relatives in Nagpur, Mrs. Kulkarni visits an outpatient diagnostics "
            "lab for urgent blood tests and an ultrasound. She authorizes an electronic payment "
            "of ₹8,500 to a newly encountered merchant UPI ID "
            "('UPI-apexcare.reception@icici'). The recipient has zero prior history in the "
            "banking cluster, but the payment leaves 98.3% of her balance intact and occurs "
            "during evening clinic hours (7:30 PM). The system flags this for two-step review "
            "rather than outright blocking."
        ),
        payment={
            "payer_name": "Savitri Devi Kulkarni",
            "payer_phone": "+91 98201 44521",
            "payer_account": "ACC-9041-3321-7788",
            "payee_name": "Apex Care Diagnostics Clinic",
            "payee_account": "UPI-apexcare.reception@icici",
            "memo": "Diagnostic lab tests and ultrasound fee",
            "family_contact": "+91 98201 99882 (Son: Anand Kulkarni)",
            "tx_type": TxType.PAYMENT.value,
            "amount": 8500.00,
            "payer_balance_before": 490000.00,
            "payee_balance_before": 42000.00,
            "payee_is_merchant": True,
            "timestamp": "2026-10-17T19:30:00+05:30",
            "language": Language.EN.value,
        },
        expected_decision=DecisionKind.REVIEW,
        expected_risk=Level.MEDIUM,
        expected_reasons=[
            ReasonCode.NEW_RECIPIENT,
        ],
        granite_prompt_preview=(
            "Decision: REVIEW. Risk: MEDIUM.\n"
            "Reasons:\n"
            "- NEW_RECIPIENT (MEDIUM): The receiving account is new or rarely used.\n"
            "Language: English.\n"
            "Write two or three calm, simple sentences warning an elderly customer. "
            "Suggest they verify the merchant name at the counter before completing the payment. "
            "Do not mention any numbers, names or links."
        ),
        family_alert_preview=(
            "ℹ️ [ShieldZ Advisory] Savitri Devi initiated a ₹8,500 payment to a new recipient "
            "(Apex Care Diagnostics). Status: Held for customer PIN confirmation. "
            "No balance drain detected."
        ),
    ),
}


def get_scenarios() -> dict[str, DemoScenario]:
    """Returns all configured demo scenarios."""
    return SCENARIOS


def get_scenario(scenario_id: str) -> DemoScenario:
    """Retrieves a single scenario by ID."""
    if scenario_id not in SCENARIOS:
        raise KeyError(f"Unknown scenario ID {scenario_id!r}. Choose from: {list(SCENARIOS)}")
    return SCENARIOS[scenario_id]


def verify_scenarios() -> bool:
    """Validates that all scenarios strictly adhere to Pydantic contracts."""
    print("Verifying ShieldZ Demo Scenarios against contracts.py...")
    for key, sc in SCENARIOS.items():
        try:
            req = sc.to_payment_request()
            assert req.amount > 0, "amount must be > 0"
            assert req.payer_balance_before >= 0, "balance must be >= 0"
            print(f"  [OK] {sc.title} (payer: {req.payer_name}, tx_type: {req.tx_type})")
        except Exception as exc:
            print(f"  [FAIL] {key}: {exc}", file=sys.stderr)
            return False
    print("All scenarios are 100% contract compliant.")
    return True


def dump_json() -> str:
    """Serializes scenarios to formatted JSON for the UI and external runners."""
    payload = {
        key: {
            "id": sc.id,
            "title": sc.title,
            "category": sc.category,
            "victim_profile": sc.victim_profile,
            "storyline": sc.storyline,
            "payment": sc.payment,
            "expected_decision": sc.expected_decision.value,
            "expected_risk": sc.expected_risk.value,
            "expected_reasons": [r.value for r in sc.expected_reasons],
            "granite_prompt_preview": sc.granite_prompt_preview,
            "family_alert_preview": sc.family_alert_preview,
        }
        for key, sc in SCENARIOS.items()
    }
    return json.dumps(payload, indent=2)


def run_live(base_url: str = "http://localhost:8000") -> int:
    """Sends each scenario's payment payload to the running ShieldZ API."""
    import time

    try:
        import httpx
    except ImportError:
        print("httpx is required to run live HTTP scenarios. Install via pip.")
        return 1

    print(f"\n--- Running ShieldZ Live Demo against {base_url} ---\n")
    client = httpx.Client(base_url=base_url, timeout=10.0)

    try:
        health = client.get("/healthz")
        print(f"Server health check: {health.status_code} -> {health.json()}\n")
    except Exception as exc:
        print(f"Error connecting to {base_url}: {exc}")
        print("Tip: Start the API with 'uvicorn shieldz.service.app:create_app --factory'.")
        return 1

    for _sc_id, sc in SCENARIOS.items():
        sep = "━" * 68
        print(sep)
        print(f"▶ {sc.title}")
        print(f"  Victim: {sc.victim_profile}")
        print(f"  Story:  {sc.storyline}")
        amount_txt = f"{sc.payment['amount']} INR ({sc.payment['tx_type']})"
        print(f"  Sending: {amount_txt} to {sc.payment['payee_name']}...")

        payment = dict(sc.payment)
        if payment["payee_account"] != SEEDED_PAYEE:  # a payee we have paid once counts as known
            payment["payee_account"] += f"-{uuid.uuid4().hex[:4]}"
        resp = client.post("/v1/score", json=payment)
        if resp.status_code != 200:
            print(f"  [ERROR] Status {resp.status_code}: {resp.text}")
            continue

        dec = resp.json()
        timing_txt = f"{dec['decision']} (Risk: {dec['risk_level']}) in {dec['server_ms']} ms"
        print(f"  ⚡ Instant Decision: {timing_txt}")
        if dec.get("reason_codes"):
            codes = [r["code"] for r in dec["reason_codes"]]
            print(f"  🔍 Reason Codes:   {', '.join(codes)}")

        decision_id = dec["decision_id"]
        if dec["decision"] != "ALLOW":
            print(f"  ⏳ Polling explanation for decision {decision_id[:8]}...")
            explanation_found = False
            for _ in range(25):
                exp_resp = client.get(f"/v1/explanations/{decision_id}")
                if exp_resp.status_code == 200:
                    exp_data = exp_resp.json()
                    print(f'  ✍️  Granite Warning ({exp_data["source"]}): "{exp_data["text"]}"')
                    explanation_found = True
                    break
                time.sleep(1.0)
            if not explanation_found:
                print(
                    "  ℹ️  Explanation job still queued in outbox "
                    "(worker still generating or not running)."
                )

            print(f'  📱 Family Alert Dispatched: "{sc.family_alert_preview}"')
        print()

    print("━" * 68)
    print("Demo scenarios completed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ShieldZ Demo Scenarios")
    parser.add_argument("--list", action="store_true", help="List summary of all scenarios")
    parser.add_argument("--show", type=str, help="Show full details of a specific scenario ID")
    parser.add_argument("--json", action="store_true", help="Output all scenarios as JSON")
    parser.add_argument(
        "--verify", action="store_true", help="Validate scenarios against contracts"
    )
    parser.add_argument("--run", action="store_true", help="Send scenarios to running ShieldZ API")
    parser.add_argument("--url", type=str, default="http://localhost:8000", help="API base URL")

    args = parser.parse_args()

    if args.list:
        print("Available ShieldZ Demo Scenarios:")
        for sc_id, sc in SCENARIOS.items():
            print(f"  • [{sc_id}] {sc.title}")
            exp_text = f"{sc.expected_decision.value} ({sc.expected_risk.value})"
            print(f"      Category: {sc.category} | Expected: {exp_text}")
        return 0

    if args.show:
        sc = get_scenario(args.show)
        print(f"Title:    {sc.title}")
        print(f"Category: {sc.category}")
        print(f"Victim:   {sc.victim_profile}")
        print(f"\nStory:\n{sc.storyline}")
        print(f"\nPayment Request Contract:\n{json.dumps(sc.payment, indent=2)}")
        print(f"\nExpected Decision: {sc.expected_decision.value} (Risk: {sc.expected_risk.value})")
        print(f"Expected Reasons:  {[r.value for r in sc.expected_reasons]}")
        print(f"\nGranite Prompt Preview:\n{sc.granite_prompt_preview}")
        print(f"\nFamily Alert Preview:\n{sc.family_alert_preview}")
        return 0

    if args.json:
        print(dump_json())
        return 0

    if args.verify:
        return 0 if verify_scenarios() else 1

    if args.run:
        return run_live(args.url)

    verify_scenarios()
    print("\nRun with --help to see execution options.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

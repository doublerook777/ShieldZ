# 🐤 ShieldZ Canary Leak Audit Scorecard

**Result:** ✅ PASS (0 Leaks)  
**Environment:** `local` (`arm64`)  
**Git SHA:** `daad8526bb`  
**Timestamp:** `2026-10-17T13:47:17.420775+00:00`  

---

### Audit Summary
| Metric | Value | Requirement | Status |
|---|---|---|---|
| **Canary Identities Replayed** | **1,000** | 1,000 | ✅ |
| **Total Sinks Scanned** | **6** | All registered + catch-all | ✅ |
| **Total Volume Scanned** | **631,919 bytes** | > 0 | ✅ |
| **Exact PII Leaks** | **0** | **0** | ✅ |
| **Variant PII Leaks** | **0** | **0** | ✅ |
| **Partial PII Leaks** | **0** | **0** | ✅ |
| **Positive Control (Easter Eggs)** | **✅ 10/10** | Exactly 10/10 | ✅ |
| **Negative Control (Decoys)** | **✅ 0 / 1000 hits** | 0 decoy hits | ✅ |

---

### Sinks Scanned
| Sink Name | Bytes Inspected |
|---|---|
| `app_log` | 511,920 bytes |
| `audit_chain` | 0 bytes |
| `history_sqlite` | 0 bytes |
| `http_responses` | 119,999 bytes |
| `outbox_sqlite` | 0 bytes |
| `prompt_journal` | 0 bytes |

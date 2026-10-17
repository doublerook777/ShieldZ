# 🐤 ShieldZ Canary Leak Audit Scorecard

**Result:** ✅ PASS (0 Leaks)  
**Environment:** `linuxone` (`s390x`)  
**Git SHA:** `287e4f2cb4`  
**Timestamp:** `2026-10-17T14:10:40.214818+00:00`  

---

### Audit Summary
| Metric | Value | Requirement | Status |
|---|---|---|---|
| **Canary Identities Replayed** | **1,000** | 1,000 | ✅ |
| **Total Sinks Scanned** | **6** | All registered + catch-all | ✅ |
| **Total Volume Scanned** | **281,999 bytes** | > 0 | ✅ |
| **Exact PII Leaks** | **0** | **0** | ✅ |
| **Variant PII Leaks** | **0** | **0** | ✅ |
| **Partial PII Leaks** | **0** | **0** | ✅ |
| **Positive Control (Easter Eggs)** | **✅ 10/10** | Exactly 10/10 | ✅ |
| **Negative Control (Decoys)** | **✅ 0 / 1000 hits** | 0 decoy hits | ✅ |

---

### Sinks Scanned
| Sink Name | Bytes Inspected |
|---|---|
| `app_log` | 162,000 bytes |
| `audit_chain` | 0 bytes |
| `history_sqlite` | 0 bytes |
| `http_responses` | 119,999 bytes |
| `outbox_sqlite` | 0 bytes |
| `prompt_journal` | 0 bytes |

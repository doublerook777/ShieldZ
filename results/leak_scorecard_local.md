# 🐤 ShieldZ Canary Leak Audit Scorecard

**Result:** ✅ PASS (0 Leaks)  
**Environment:** `local` (`x86_64`)  
**Git SHA:** `029b026494`  
**Timestamp:** `2026-10-17T17:08:34.700368+00:00`  

---

### Audit Summary
| Metric | Value | Requirement | Status |
|---|---|---|---|
| **Canary Identities Replayed** | **1,000** | 1,000 | ✅ |
| **Total Sinks Scanned** | **11** | All registered + catch-all | ✅ |
| **Total Volume Scanned** | **2,146,647 bytes** | > 0 | ✅ |
| **Exact PII Leaks** | **0** | **0** | ✅ |
| **Variant PII Leaks** | **0** | **0** | ✅ |
| **Partial PII Leaks** | **0** | **0** | ✅ |
| **Positive Control (Easter Eggs)** | **✅ 10/10** | Exactly 10/10 | ✅ |
| **Negative Control (Decoys)** | **✅ 0 / 1000 hits** | 0 decoy hits | ✅ |

---

### Sinks Scanned
| Sink Name | Bytes Inspected |
|---|---|
| `app_log` | 434,188 bytes |
| `audit_chain` | 374,575 bytes |
| `catch_all:audit/checkpoints.jsonl` | 5,499 bytes |
| `catch_all:history.sqlite-shm` | 32,768 bytes |
| `catch_all:history.sqlite-wal` | 0 bytes |
| `catch_all:outbox.sqlite-shm` | 32,768 bytes |
| `catch_all:outbox.sqlite-wal` | 0 bytes |
| `history_sqlite` | 106,496 bytes |
| `http_responses` | 510,288 bytes |
| `outbox_sqlite` | 438,272 bytes |
| `prompt_journal` | 211,793 bytes |

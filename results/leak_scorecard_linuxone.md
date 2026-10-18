# 🐤 ShieldZ Canary Leak Audit Scorecard

**Result:** ✅ PASS (0 Leaks)  
**Environment:** `linuxone` (`s390x`)  
**Git SHA:** `unknown`  
**Timestamp:** `2026-10-18T08:00:53.455507+00:00`  

---

### Audit Summary
| Metric | Value | Requirement | Status |
|---|---|---|---|
| **Canary Identities Replayed** | **1,000** | 1,000 | ✅ |
| **Total Sinks Scanned** | **11** | All registered + catch-all | ✅ |
| **Total Volume Scanned** | **3,760,623 bytes** | > 0 | ✅ |
| **Exact PII Leaks** | **0** | **0** | ✅ |
| **Variant PII Leaks** | **0** | **0** | ✅ |
| **Partial PII Leaks** | **0** | **0** | ✅ |
| **Positive Control (Easter Eggs)** | **✅ 10/10** | Exactly 10/10 | ✅ |
| **Negative Control (Decoys)** | **✅ 0 / 1000 hits** | 0 decoy hits | ✅ |

---

### Sinks Scanned
| Sink Name | Bytes Inspected |
|---|---|
| `app_log` | 359,879 bytes |
| `audit_chain` | 396,978 bytes |
| `catch_all:audit/checkpoints.jsonl` | 2,618 bytes |
| `catch_all:history.sqlite-shm` | 32,768 bytes |
| `catch_all:history.sqlite-wal` | 0 bytes |
| `catch_all:outbox.sqlite-shm` | 32,768 bytes |
| `catch_all:outbox.sqlite-wal` | 0 bytes |
| `history_sqlite` | 106,496 bytes |
| `http_responses` | 1,084,884 bytes |
| `outbox_sqlite` | 811,008 bytes |
| `prompt_journal` | 933,224 bytes |

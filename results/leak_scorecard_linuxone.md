# 🐤 ShieldZ Canary Leak Audit Scorecard

**Result:** ✅ PASS (0 Leaks)  
**Environment:** `linuxone` (`s390x`)  
**Git SHA:** `unknown`  
**Timestamp:** `2026-10-17T20:10:36.002144+00:00`  

---

### Audit Summary
| Metric | Value | Requirement | Status |
|---|---|---|---|
| **Canary Identities Replayed** | **1,000** | 1,000 | ✅ |
| **Total Sinks Scanned** | **11** | All registered + catch-all | ✅ |
| **Total Volume Scanned** | **4,785,991 bytes** | > 0 | ✅ |
| **Exact PII Leaks** | **0** | **0** | ✅ |
| **Variant PII Leaks** | **0** | **0** | ✅ |
| **Partial PII Leaks** | **0** | **0** | ✅ |
| **Positive Control (Easter Eggs)** | **✅ 10/10** | Exactly 10/10 | ✅ |
| **Negative Control (Decoys)** | **✅ 0 / 1000 hits** | 0 decoy hits | ✅ |

---

### Sinks Scanned
| Sink Name | Bytes Inspected |
|---|---|
| `app_log` | 383,023 bytes |
| `audit_chain` | 449,632 bytes |
| `catch_all:audit/checkpoints.jsonl` | 2,355 bytes |
| `catch_all:history.sqlite-shm` | 32,768 bytes |
| `catch_all:history.sqlite-wal` | 0 bytes |
| `catch_all:outbox.sqlite-shm` | 32,768 bytes |
| `catch_all:outbox.sqlite-wal` | 0 bytes |
| `history_sqlite` | 106,496 bytes |
| `http_responses` | 1,552,391 bytes |
| `outbox_sqlite` | 1,073,152 bytes |
| `prompt_journal` | 1,153,406 bytes |

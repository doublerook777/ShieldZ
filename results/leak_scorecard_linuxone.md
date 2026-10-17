# 🐤 ShieldZ Canary Leak Audit Scorecard

**Result:** ✅ PASS (0 Leaks)  
**Environment:** `linuxone` (`s390x`)  
**Git SHA:** `1905f3cf34`  
**Timestamp:** `2026-10-17T18:29:06.467801+00:00`  

---

### Audit Summary
| Metric | Value | Requirement | Status |
|---|---|---|---|
| **Canary Identities Replayed** | **1,000** | 1,000 | ✅ |
| **Total Sinks Scanned** | **11** | All registered + catch-all | ✅ |
| **Total Volume Scanned** | **16,694,276 bytes** | > 0 | ✅ |
| **Exact PII Leaks** | **0** | **0** | ✅ |
| **Variant PII Leaks** | **0** | **0** | ✅ |
| **Partial PII Leaks** | **0** | **0** | ✅ |
| **Positive Control (Easter Eggs)** | **✅ 10/10** | Exactly 10/10 | ✅ |
| **Negative Control (Decoys)** | **✅ 0 / 1000 hits** | 0 decoy hits | ✅ |

---

### Sinks Scanned
| Sink Name | Bytes Inspected |
|---|---|
| `app_log` | 3,009,101 bytes |
| `audit_chain` | 4,118,951 bytes |
| `catch_all:audit/checkpoints.jsonl` | 26,046 bytes |
| `catch_all:history.sqlite-shm` | 98,304 bytes |
| `catch_all:history.sqlite-wal` | 0 bytes |
| `catch_all:outbox.sqlite-shm` | 131,072 bytes |
| `catch_all:outbox.sqlite-wal` | 24,752 bytes |
| `history_sqlite` | 991,232 bytes |
| `http_responses` | 1,382,039 bytes |
| `outbox_sqlite` | 4,583,424 bytes |
| `prompt_journal` | 2,329,355 bytes |

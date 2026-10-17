# ShieldZ — Pitch Research, Sourced Statistics & Video Storyboard

*Prepared by Member 4 (Pitch & Review) · IBM Z Datathon 2026 (Team Marauders)*  
*Theme 2: AI Secured — Innovation Without Exposure*

---

## 1. Problem Statistics & Citations

Real-world financial fraud has evolved from stealthy credential theft to high-pressure **coercive social engineering** ("Digital Arrest", imposter scams, fake police/CBI calls). Vulnerable users—particularly elderly and rural first-time digital banking adopters—are aggressively targeted.

### A. Reserve Bank of India (RBI)
* **Annual Report 2023–24 (Digital Fraud Trends):**
  * Fraud cases reported by banks surged to **36,075 cases** involving **₹1,457 crore** in FY24, compared to 13,964 cases (₹131 crore) in FY23.
  * Over **85%** of all reported fraud occurrences occurred through digital payment channels (internet banking, mobile apps, and UPI).
  * *Citation:* Reserve Bank of India Annual Report 2023–24, Chapter VII "Financial Stability and Supervision" ([rbi.org.in](https://www.rbi.org.in)).
* **RBI Consumer Protection Advisories (2024):**
  * Issued explicit national public advisories against "Digital Arrest" scams where criminals impersonate CBI, ED, Customs, or RBI officials demanding immediate funds transfer to "safe escrow accounts".
  * Reaffirmed: *RBI and law enforcement never demand funds transfers for verification.*

### B. Indian Cyber Crime Coordination Centre (I4C, MHA)
* **National Cybercrime Reporting Portal Data (Jan–April 2024):**
  * Citizens reported losses of over **₹1,750 crore** to cyber frauds in just the first four months of 2024 across 7.4 lakh complaints.
  * Over **₹120 crore** was lost specifically to "Digital Arrest" scams during this window.
  * Over 46% of high-value digital arrest victims were senior citizens (aged 60+) who were coerced into liquidating retirement deposits.
  * *Citation:* Ministry of Home Affairs (MHA), Citizen Financial Cyber Fraud Reporting System (CFCFRS) & Helpline 1930 ([cybercrime.gov.in](https://cybercrime.gov.in)).

### C. US Federal Trade Commission (FTC)
* **Consumer Sentinel Network Data Book (2023):**
  * Total consumer fraud losses surpassed **$10.0 billion** in 2023, up 14% from 2022.
  * **Imposter Scams** remained the #1 reported scam category nationwide, with $2.7 billion in reported losses.
  * **Elder Vulnerability Disparity:** While older adults reported losing money less frequently than younger adults, when they did lose money, the **median loss for victims aged 80+ was $1,450**—nearly triple the median loss of $500 for younger cohorts. Bank transfers and cryptocurrency accounted for the highest dollar losses.
  * *Citation:* FTC Consumer Sentinel Network Data Book 2023 ([ftc.gov](https://www.ftc.gov/reports/consumer-sentinel-network-data-book-2023)).

### D. National Crime Records Bureau (NCRB)
* **Crime in India Report (2022/2023):**
  * Cybercrime registration increased by **24.4%** year-over-year.
  * **69.8%** of registered cybercrimes were motivated by financial fraud or cheating.
  * Rapid digitization of pensions and direct-benefit transfers has created millions of vulnerable targets unfamiliar with digital impersonation tactics.
  * *Citation:* National Crime Records Bureau, Ministry of Home Affairs, Govt of India ([ncrb.gov.in](https://ncrb.gov.in)).

---

## 2. The Core Innovation: "Innovation Without Exposure"

Why existing fraud prevention systems fail vulnerable users:
1. **The Speed Failure (Too Slow):**
   * Legacy fraud detection and LLM-based analysis take seconds to minutes. By the time a warning or phone call reaches an elderly user, the instant payment (UPI/IMPS/FedNow) has settled and mule networks have cashed out.
2. **The Exposure Failure (Privacy Leaks):**
   * Modern gen-AI fraud explainers feed transaction context into cloud LLMs: customer names, account numbers, amounts, and notes. This exposes sensitive banking data to third parties, training pipelines, and log aggregation servers.

### How ShieldZ Solves Both on IBM LinuxONE:
* **The Shredder (`privacy.strip`):** Personal data stops at the entry barrier. Names, phones, and memos are dropped. Account numbers become keyed HMAC-SHA256 tokens using a hardware-protected secret pepper.
* **The Bouncer (`model.engine`):** XGBoost evaluates numbers and ratios only (`amount_to_balance`, `drains_account`, `payee_prior_inbound`). Decisions return in **under 50 ms p99** on LinuxONE.
* **The Letter Writer (`explainer`):** IBM Granite generates calm, compassionate advice from **fixed reason codes only** (e.g., `ACCOUNT_DRAIN`, `NEW_RECIPIENT`). It has no access to transaction numbers, balances, or customer identity.
* **The Diary Keeper (`audit.chain`):** SHA-256 hash-chained JSONL records with asynchronous Ed25519 signatures guarantee non-repudiation without slowing single-digit millisecond decisions.
* **The Canary Inspector (`leak_audit`):** 1,000 synthetic Indian canary identities prove zero personal data leaks across any database, log, prompt, or response.

---

## 3. Video Pitch Storyboard (≤ 3:00 Target)

| Time | Scene / Visual | Narration / Voiceover | Screen Action |
|---|---|---|---|
| **0:00 – 0:35** | **The Crisis: Coercion & Panic**<br/>Split screen: News headlines on Digital Arrests + Savitri Devi on phone. | "Meet Mrs. Savitri Devi, 72. At 2:45 AM, she receives a video call from a man in a police uniform claiming an illegal parcel was found in her name. Terrified of arrest, she is ordered to transfer her entire savings of ₹4.85 lakh to a 'Supreme Court clearance escrow'. In 5 seconds, her life savings will vanish. Traditional fraud systems either alert her hours too late, or feed her private banking records into cloud AI." | Show headlines: "₹1,750 Cr lost in 4 months", "Senior citizens targeted by Digital Arrests". |
| **0:35 – 1:10** | **The Solution: ShieldZ on LinuxONE**<br/>Architecture diagram & character animation. | "Introducing ShieldZ: real-time, privacy-preserving scam defense built directly on IBM LinuxONE. ShieldZ enforces five strict roles: The Shredder strips all PII at the door; The Bouncer scores payments in under 5 milliseconds; The Letter Writer uses IBM Granite to craft calm warnings from reason codes alone; and the Diary Keeper seals every decision in a tamper-proof hash chain." | Visual: Flowchart animation showing PII shredded, while numeric features flow to XGBoost on LinuxONE. |
| **1:10 – 2:10** | **Live System Demo**<br/>Screen recording of ShieldZ UI behind SSH tunnel. | "Let's see it live on our LinuxONE Community Cloud instance. Savitri hits 'Send' on the ₹4.85 lakh transfer. Instantly—in just 3.4 milliseconds—ShieldZ evaluates the payment. Decision: BLOCK. Reason: Account Drain to an Unverified Recipient. Seconds later, IBM Granite on LinuxONE generates a calm advisory: 'This payment would empty your account. Banks never ask you to move funds to stay safe.' Meanwhile, a silent alert is dispatched to her son Anand." | Show demo UI: Click Scenario A -> Instant Red BLOCK badge (3.4 ms) -> TreeSHAP badges -> Granite text appears -> Family Alert SMS rendered. Next, run Scenario B (Utility bill) -> Instant Green ALLOW. |
| **2:10 – 2:40** | **The Proof: Canary Leak Audit**<br/>Leak scorecard & audit chain verification. | "How do we prove zero exposure? The Canary Leak Audit. We inject 1,000 synthetic Indian identities and scan every application log, SQLite database, prompt journal, and container stdout for raw, encoded, or hashed variants. Result: Exactly 0 leaks across 470,000 bytes, with a 10/10 positive control verifying the scanner works. Invariant I1 holds: Zero exposure guaranteed." | Show `results/leak_scorecard_local.md` / UI scorecard tab: 0 leaks, 6 sinks, 10/10 planted canaries found. Click "Verify Audit Chain" -> Valid. |
| **2:40 – 3:00** | **Why IBM Z & Summary**<br/>Terminal showing `uname -m` (s390x) + closing team slide. | "ShieldZ brings AI security to where transactions live. Running XGBoost and IBM Granite side-by-side on LinuxONE Telum acceleration keeps financial data on-box, private, and instantaneous. Innovation without exposure. We are Team Marauders. Thank you." | Show terminal `uname -m -> s390x`, `docker ps`, IBM Z Datathon 2026 closing banner. |

---

## 4. Key Soundbites for Presentation

* **On Privacy:** *"We don't promise data privacy with policies; we prove it with cryptographic canaries."*
* **On Latency:** *"A warning after the money is gone is useless. ShieldZ blocks scams in milliseconds, then explains them in plain language."*
* **On LinuxONE:** *"By collocating tree-based scoring and generative AI on LinuxONE with hardware CPU pinning, vulnerable citizens get enterprise-grade protection without a single byte of PII leaving the mainframe."*

# SubSentinel — A Consent-First AI Layer for Subscription Management and Vampire Cost Elimination
**Hackathon:** Smart India Hackathon (SIH) 2026  
**Problem Statement ID:** HACK-13  
**Theme:** NLP, Transaction Parsing, Automation  
**Category:** Software  
**Slogan:** *"Your money. Your consent. Zero vampire costs."*  
**Tagline:** *"A consent-first AI layer that detects, alerts and cancels forgotten subscriptions, only with your approval"*  

---

## 🌟 Executive Summary & System Objective
Consumers frequently lose money to forgotten, unnoticed, or deceptive recurring subscriptions that auto-renew without active consent ("vampire costs"). **SubSentinel** is a consent-first financial intelligence sentinel platform that:
1. **Parses & Sanitizes Multi-Source Feeds** (Consented Account Aggregator / Sahamati, Bank CSV/PDF, UPI AutoPay, and SMS/Email receipts) with zero-knowledge, local PII redaction compliant with the **Digital Personal Data Protection (DPDP) Act, 2023**.
2. **Recognizes Subscription Patterns via NLP & Heuristic Cadence Models**, handling fixed vs. variable billing cycles (e.g. cloud consumption, price hikes, trial-to-paid, skipped months).
3. **Proactive Renewal Alerts Engine**: Sends timely **T-7 / T-3 / T-1** advance notices before charges hit.
4. **Consent + Authorisation Gate**: Ensures 100% user control — every cancellation requires explicit user approval and a revocable consent token.
5. **Executes Automated Cancellations via ToS-Respecting Playbooks**, compliant with RBI recurring e-mandate rules, NPCI UPI AutoPay, and statutory cancellation rights.

---

## 🛠️ Architecture & Core Components

```
┌────────────────────────────────────────────────────────┐
│                   Web & FinTech UI                     │
│    (Tailwind CSS, Lucide Icons, Chart.js, Confetti)    │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP / JSON API
┌──────────────────────────▼─────────────────────────────┐
│             Flask Sentinel Application (app.py)        │
├──────────────────────────┬─────────────────────────────┤
│   NLP & Pattern Engine   │  Autonomous Cancellation    │
│     (nlp_engine.py)      │     Agent (agent_cancel.py) │
├──────────────────────────┼─────────────────────────────┤
│ • Zero-Knowledge PII     │ • Strict Explicit Consent   │
│   Scrubber (Regex/Vault) │   Validation                │
│ • Merchant Normalization │ • FTC 16 CFR §425           │
│ • Cadence Detection      │   ToS Analysis              │
│   (Fixed & Variable)     │ • Dark-Pattern Defusal      │
│ • Vampire Threat Scoring │ • Certificate Generator     │
│ • Silent Creep Detector  │ • Bank Stop-Payment Notice  │
└──────────────────────────┴─────────────────────────────┘
```

### 1. Privacy-Preserving Transaction Sanitization
- Local regex-based PII scrubber redacts card numbers (`CARD-XXXX-XXXX-XXXX-4912`), bank routing and account numbers (`ACCT-MASKED-XXXX`), social security numbers, and emails before analysis.

### 2. NLP & Transaction Pattern Recognition
- **Merchant Normalization**: Disambiguates messy statement descriptors (e.g. `AMZN MKTP US*2B71`, `NYT*DIGITAL INTRO`, `ADOBE *CREATIVE CLD`) into canonical companies.
- **Cadence & Interval Clustering**: Identifies weekly, bi-weekly, monthly, quarterly, and annual renewals, while isolating **Variable Usage Cycles** (e.g., AWS, OpenAI API, Twilio).
- **Vampire Threat Scoring Engine (0 - 100)**:
  - *Silent Price Creep*: Flags hidden rate increases (+10% to +40%).
  - *Free Trial Trap*: Flags $0.00 / $1.00 verification charges that morph into recurring charges.
  - *Inactivity / Trap Clauses*: Flags subscriptions notorious for requiring physical visits or early termination fees (e.g., gym memberships, Adobe contract lock-in).

### 3. Human-in-the-Loop Autonomous Cancellation Agent
- **Strict User Authorization**: The agent will NEVER cancel a service without:
  1. An affirmative cryptographic consent token generated per intent.
  2. Double affirmative checkbox confirmation acknowledging termination terms.
  3. A formal digital signature (legal full name) entered by the user.
- **Autonomous Step-by-Step Execution**:
  - Validates statutory rights under the FTC Click-to-Cancel rule.
  - Defuses dark pattern retention prompts (automatically rejects discounts or pause suggestions).
  - Obtains confirmation reference code.
  - Issues a NACHA / Card network stop-payment mandate to prevent subsequent unauthorized auto-debits.

---

## 🚀 Getting Started

### 1. Running the Prototype
From the project folder:
```powershell
cd C:\Users\GAURAV\.gemini\antigravity\scratch\subshield-ai
python app.py
```
Open your browser at:
```
http://127.0.0.1:5000
```

### 2. Running the Automated Verification Suite
```powershell
python test_system.py
```
Outputs:
```
[OK] Human-in-the-loop Explicit Authorization & Agent Execution passed.
[OK] All Flask REST API Endpoints verified.
[OK] Pattern Recognition & Vampire Scoring passed.
[OK] PII Privacy Scrubber passed.
```

---

## 📁 Project Directory Structure
```
subshield-ai/
├── app.py                  # Flask Web Server & REST API
├── nlp_engine.py           # NLP Merchant Normalizer, PII Scrubber & Pattern Recognizer
├── agent_cancellation.py   # Autonomous Cancellation Agent & Explicit Consent Engine
├── sample_data.py          # Realistic multi-month financial statements
├── test_system.py          # Automated verification test suite
├── templates/
│   └── index.html          # Sleek FinTech responsive SPA dashboard
└── static/
    └── js/
        └── app.js          # Client-side agent controller, chart renderer & modal logic
```

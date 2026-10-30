"""
SubSentinel AI - Gemini AI Service
Provides LLM-powered Vampire Cost Analysis, Cancellation Letter Drafting, and Interactive Advice.
Works both with live Google Gemini API (GEMINI_API_KEY) and offline intelligent fallback.
"""

import os
import json
import urllib.request
import urllib.error

DEFAULT_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

class GeminiService:
    @staticmethod
    def get_api_key(custom_key=None):
        return custom_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""

    @classmethod
    def call_gemini(cls, prompt: str, api_key: str = None, system_instruction: str = None) -> dict:
        key = cls.get_api_key(api_key)
        if not key:
            return {
                "success": False,
                "error": "GEMINI_API_KEY_MISSING",
                "message": "Gemini API key is not configured. Using local intelligence engine."
            }

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 1000
            }
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        last_error = None
        for model in DEFAULT_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_body = response.read().decode("utf-8")
                    data = json.loads(res_body)
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)
                        return {
                            "success": True,
                            "model": model,
                            "text": text,
                            "source": "gemini_api"
                        }
            except urllib.error.HTTPError as e:
                err_text = e.read().decode("utf-8", errors="ignore")
                last_error = f"HTTP {e.code}: {err_text[:200]}"
                continue
            except Exception as e:
                last_error = str(e)
                continue

        return {
            "success": False,
            "error": "API_CALL_FAILED",
            "message": last_error or "Unable to reach Gemini API"
        }

    @classmethod
    def analyze_subscription(cls, sub: dict, api_key: str = None) -> dict:
        name = sub.get("merchant_name", "Unknown Subscription")
        amount = sub.get("current_amount", sub.get("monthly_equivalent", 0.0))
        billing = sub.get("billing_cycle", "Monthly")
        threat = sub.get("vampire_threat_score", 50)
        days = sub.get("days_until_renewal", 7)
        category = sub.get("category", "Services")

        prompt = f"""
You are SubSentinel AI, an expert consumer protection AI operating under India's DPDP Act 2023 and RBI e-Mandate Framework (SIH 2026 Problem Statement HACK-13).
Analyze this recurring subscription:
- Merchant: {name}
- Cost: ₹{amount:.2f} ({billing})
- Vampire Threat Score: {threat}/100
- Days until next charge: {days} days
- Category: {category}

Provide:
1. Executive Risk Summary (2-3 sentences explaining why this is a vampire cost)
2. Dark Pattern Identification (e.g. passive auto-renewal, complex cancellation loops, price creep)
3. Action Plan (1-2 clear next steps)
4. Formal Cancellation / Dispute Clause citing RBI/2019-20/150 and DPDP Act Section 6(1) for immediate mandate revocation.

Format response clearly with headings.
"""
        gemini_result = cls.call_gemini(
            prompt=prompt,
            api_key=api_key,
            system_instruction="You are SubSentinel AI, a consumer financial guardian specializing in subscription optimization."
        )

        if gemini_result.get("success"):
            return {
                "success": True,
                "merchant": name,
                "analysis_text": gemini_result["text"],
                "source": "gemini_api",
                "model": gemini_result.get("model")
            }

        # Offline Intelligent Fallback (Ensures site never fails)
        fallback_analysis = f"""### 🛡️ SubSentinel Risk Analysis for {name}
**Vampire Threat Score:** {threat}/100 ({'High Risk' if threat >= 60 else 'Moderate Risk'})

**1. Executive Risk Assessment:**
{name} renews in {days} days for ₹{amount:.2f}. Recurring auto-debit pattern matches passive subscription drain. Under the current trajectory, this service will drain ₹{amount * 12:.2f} annually without active utility monitoring.

**2. Identified Dark Pattern Indicators:**
- **Automated Mandate Inertia:** Frictionless sign-up with obscured opt-out mechanics.
- **Pre-Debit Window Alert:** Charge is scheduled within {days} days, requiring immediate user authorization.

**3. Action Recommendation:**
Initiate 3-Gate user-authorized cancellation or request a pause before next billing cycle to prevent irreversible e-mandate execution.

**4. Statutory Legal Revocation Notice:**
*\"Notice is hereby served under RBI Circular RBI/2019-20/150 and DPDP Act 2023. Explicit user consent for recurring auto-debit towards {name} is hereby revoked. Immediate cessation of merchant debit mandates is demanded effective immediately.\"*"""

        return {
            "success": True,
            "merchant": name,
            "analysis_text": fallback_analysis,
            "source": "subsentinel_nlp_engine",
            "note": "Connect your Gemini API Key in Settings to enable live Google Gemini 2.5/2.0 reasoning."
        }

    @classmethod
    def generate_cancellation_letter(cls, sub: dict, user_name: str, reason: str, api_key: str = None) -> dict:
        name = sub.get("merchant_name", "Service Provider")
        amount = sub.get("current_amount", sub.get("monthly_equivalent", 0.0))

        prompt = f"""
Write a formal, legally grounded subscription cancellation and e-mandate revocation letter:
- User Name: {user_name}
- Merchant/Service: {name}
- Subscription Amount: ₹{amount:.2f}
- Reason: {reason}
- Applicable Framework: RBI Circular RBI/2019-20/150 on e-Mandate Processing, NPCI UPI Autopay guidelines, and India DPDP Act 2023.

Keep it professional, polite yet legally firm, requiring confirmation of termination within 48 hours.
"""
        gemini_result = cls.call_gemini(
            prompt=prompt,
            api_key=api_key,
            system_instruction="You are a legal assistant drafting consumer rights and mandate termination letters."
        )

        if gemini_result.get("success"):
            return {
                "success": True,
                "letter_text": gemini_result["text"],
                "source": "gemini_api"
            }

        # Fallback template
        fallback_letter = f"""Date: {urllib.request.datetime.date.today().strftime('%B %d, %Y')}

To: Customer Support & Billing Department, {name}

Subject: URGENT: Revocation of Standing e-Mandate & Termination of Subscription Account

Dear Billing Team,

I am writing to formally communicate the immediate cancellation of my recurring subscription for {name} (recurring fee: ₹{amount:.2f}).

In accordance with:
1. Reserve Bank of India (RBI) Circular RBI/2019-20/150 on Processing of e-Mandates for recurring transactions,
2. Digital Personal Data Protection (DPDP) Act 2023,

I hereby withdraw all authorization and consent for any future automatic debit transactions or standing payment instructions linked to my account/card/UPI VPA.

Reason for Termination: {reason}.

Please confirm the cancellation in writing and ensure no further debits occur.

Sincerely,
{user_name}
Authorized via SubSentinel AI Guardian (SIH 2026)"""

        return {
            "success": True,
            "letter_text": fallback_letter,
            "source": "subsentinel_template_engine"
        }

"""
SubSentinel AI - Flask Application Server & API
A Consent-First AI Layer for Subscription Management & Vampire Cost Elimination (SIH 2026 | HACK-13)
"""

import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from nlp_engine import PrivacyScrubber, TransactionParser, PatternRecognitionEngine
from agent_cancellation import CancellationAgent
from sample_data import generate_sample_statement
from gemini_service import GeminiService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static"
)
app.secret_key = "subsentinel-ai-secure-secret-key-2026"

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(os.path.join(BASE_DIR, "static"), filename)

# NOTE: Vercel runs stateless serverless functions — each request may be a fresh instance.
# We keep a module-level state dict BUT also support stateless fallback in GET /api/subscriptions.
# For a prototype, we re-generate from default profile when state is empty.

_default_profile = "tech_enthusiast"

def build_state_from_profile(profile="tech_enthusiast"):
    """Generate fresh analysis state from a sample profile."""
    raw_sample = generate_sample_statement(profile)
    scrubbed, pii_counts = PrivacyScrubber.scrub_text(raw_sample)
    lines = scrubbed.splitlines()
    txs = [TransactionParser.parse_line(l) for l in lines if TransactionParser.parse_line(l)]
    analysis = PatternRecognitionEngine.analyze_transactions(txs)
    return {
        "current_subscriptions": analysis["subscriptions"],
        "metrics": {**analysis["metrics"], "total_eliminated_drain": 0.0},
        "pii_metrics": pii_counts,
        "cancelled_certificates": {},
        "last_raw_input": raw_sample,
        "last_scrubbed_input": scrubbed,
        "alert_history": []
    }

# Module-level state (works for long-lived instances; auto-filled on serverless cold-start)
state = build_state_from_profile(_default_profile)

agent = CancellationAgent()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/subscriptions", methods=["GET"])
def get_subscriptions():
    # Serverless cold-start fix: if state is empty, regenerate from default profile
    if not state["current_subscriptions"]:
        fresh = build_state_from_profile("tech_enthusiast")
        state.update(fresh)
    return jsonify({
        "success": True,
        "subscriptions": state["current_subscriptions"],
        "metrics": state["metrics"],
        "pii_metrics": state["pii_metrics"]
    })

@app.route("/api/load-sample", methods=["POST"])
def load_sample():
    data = request.get_json() or {}
    profile = data.get("profile", "tech_enthusiast")
    raw_text = generate_sample_statement(profile)
    
    # Privacy scrubbing
    scrubbed, pii_counts = PrivacyScrubber.scrub_text(raw_text)
    state["last_raw_input"] = raw_text
    state["last_scrubbed_input"] = scrubbed
    state["pii_metrics"] = pii_counts
    
    lines = scrubbed.splitlines()
    txs = []
    for line in lines:
        parsed = TransactionParser.parse_line(line)
        if parsed:
            txs.append(parsed)
            
    analysis = PatternRecognitionEngine.analyze_transactions(txs)
    state["current_subscriptions"] = analysis["subscriptions"]
    state["metrics"] = analysis["metrics"]
    state["metrics"]["total_eliminated_drain"] = 0.0
    
    return jsonify({
        "success": True,
        "message": f"Successfully loaded and parsed profile: {profile}",
        "subscriptions": state["current_subscriptions"],
        "metrics": state["metrics"],
        "pii_metrics": state["pii_metrics"],
        "scrubbed_preview": scrubbed[:800]
    })

@app.route("/api/parse-statement", methods=["POST"])
def parse_statement():
    data = request.get_json() or {}
    raw_statement = data.get("statement_text", "")
    
    if not raw_statement.strip():
        return jsonify({"success": False, "error": "Statement text cannot be empty"}), 400
        
    # Strict Privacy Scrubbing
    scrubbed, pii_counts = PrivacyScrubber.scrub_text(raw_statement)
    state["last_raw_input"] = raw_statement
    state["last_scrubbed_input"] = scrubbed
    state["pii_metrics"] = pii_counts
    
    lines = scrubbed.splitlines()
    txs = []
    for line in lines:
        parsed = TransactionParser.parse_line(line)
        if parsed:
            txs.append(parsed)
            
    if not txs:
        return jsonify({
            "success": False, 
            "error": "Could not identify valid date/amount transaction rows. Check format (CSV: Date,Description,Amount or Bank text lines)."
        }), 400

    analysis = PatternRecognitionEngine.analyze_transactions(txs)
    state["current_subscriptions"] = analysis["subscriptions"]
    state["metrics"] = analysis["metrics"]
    state["metrics"]["total_eliminated_drain"] = 0.0
    
    return jsonify({
        "success": True,
        "parsed_transactions_count": len(txs),
        "subscriptions": state["current_subscriptions"],
        "metrics": state["metrics"],
        "pii_metrics": state["pii_metrics"],
        "scrubbed_preview": scrubbed[:800]
    })

@app.route("/api/cancel-intent", methods=["POST"])
def cancel_intent():
    data = request.get_json() or {}
    sub_id = data.get("subscription_id")
    
    # Locate subscription
    sub = next((s for s in state["current_subscriptions"] if s["id"] == sub_id), None)
    if not sub:
        return jsonify({"success": False, "error": "Subscription not found"}), 404
        
    manifest = agent.prepare_intent_manifest(sub)
    return jsonify({
        "success": True,
        "manifest": manifest,
        "subscription": sub
    })

@app.route("/api/execute-cancellation", methods=["POST"])
def execute_cancellation():
    data = request.get_json() or {}
    sub_id = data.get("subscription_id")
    
    sub = next((s for s in state["current_subscriptions"] if s["id"] == sub_id), None)
    if not sub:
        return jsonify({"success": False, "error": "Subscription not found"}), 404

    # Execution requires explicit authorization
    authorization = {
        "user_consent_granted": data.get("user_consent_granted", False),
        "consent_token": data.get("consent_token"),
        "signature_name": data.get("signature_name"),
        "reason": data.get("reason", "Vampire cost elimination")
    }

    result = agent.execute_cancellation_workflow(sub, authorization)
    
    if result.get("success"):
        # Update subscription status in session
        sub["status"] = "Cancelled"
        monthly_saved = sub.get("monthly_equivalent", 0.0)
        state["metrics"]["total_eliminated_drain"] = round(state["metrics"].get("total_eliminated_drain", 0.0) + monthly_saved, 2)
        state["metrics"]["total_monthly_drain"] = round(max(0.0, state["metrics"]["total_monthly_drain"] - monthly_saved), 2)
        state["metrics"]["projected_annual_drain"] = round(state["metrics"]["total_monthly_drain"] * 12, 2)
        state["cancelled_certificates"][sub_id] = result["certificate"]

    return jsonify(result)

@app.route("/api/send-alert", methods=["POST"])
def send_alert():
    data = request.get_json() or {}
    sub_id = data.get("subscription_id")
    channel = data.get("channel", "email") # email, push, webhook
    
    sub = next((s for s in state["current_subscriptions"] if s["id"] == sub_id), None)
    if not sub:
        return jsonify({"success": False, "error": "Subscription not found"}), 404
        
    alert_record = {
        "id": f"ALT-{len(state['alert_history'])+1}",
        "channel": channel.upper(),
        "merchant": sub["merchant_name"],
        "amount": sub["current_amount"],
        "renewal_date": sub["next_renewal"],
        "days_left": sub["days_until_renewal"],
        "vampire_threat": sub["vampire_threat_score"],
        "title": f"⚠️ SubSentinel T-Alert: {sub['merchant_name']} auto-renews in {sub['days_until_renewal']} days!",
        "body": f"RBI e-Mandate notification: Scheduled charge of ${sub['current_amount']:.2f} detected on {sub['next_renewal']}. Vampire Threat Score: {sub['vampire_threat_score']}/100. One-tap user-approved cancellation is available in your SubSentinel dashboard.",
        "timestamp": "Just now"
    }
    state["alert_history"].insert(0, alert_record)
    
    return jsonify({
        "success": True,
        "message": f"Proactive renewal alert dispatched via {channel.upper()}",
        "alert": alert_record
    })

@app.route("/api/audit-logs", methods=["GET"])
def get_audit_logs():
    return jsonify({
        "success": True,
        "audit_logs": agent.audit_log,
        "alert_history": state["alert_history"]
    })

# ─────────────────────────────────────────────────────────────
# GEMINI AI ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.route("/api/ai/analyze-subscription", methods=["POST"])
def ai_analyze_subscription():
    data = request.get_json() or {}
    sub_id = data.get("subscription_id")
    api_key = data.get("api_key")

    sub = next((s for s in state["current_subscriptions"] if s["id"] == sub_id), None)
    if not sub:
        # Fallback if state was reset: provide generic payload
        sub = {
            "merchant_name": data.get("merchant_name", "Service Provider"),
            "current_amount": float(data.get("amount", 499.0)),
            "billing_cycle": "Monthly",
            "vampire_threat_score": 75,
            "days_until_renewal": 4,
            "category": "Entertainment"
        }

    analysis = GeminiService.analyze_subscription(sub, api_key=api_key)
    return jsonify(analysis)

@app.route("/api/ai/draft-letter", methods=["POST"])
def ai_draft_letter():
    data = request.get_json() or {}
    sub_id = data.get("subscription_id")
    user_name = data.get("user_name", "SubSentinel Consumer")
    reason = data.get("reason", "Vampire cost elimination")
    api_key = data.get("api_key")

    sub = next((s for s in state["current_subscriptions"] if s["id"] == sub_id), None)
    if not sub:
        sub = {
            "merchant_name": data.get("merchant_name", "Service Provider"),
            "current_amount": float(data.get("amount", 499.0))
        }

    letter = GeminiService.generate_cancellation_letter(sub, user_name, reason, api_key=api_key)
    return jsonify(letter)

@app.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    data = request.get_json() or {}
    query = data.get("query", "").strip()
    api_key = data.get("api_key")

    if not query:
        return jsonify({"success": False, "error": "Query cannot be empty"}), 400

    active_subs = [s for s in state["current_subscriptions"] if s.get("status") != "Cancelled"]
    summary_list = [f"- {s.get('merchant_name')}: ₹{s.get('current_amount')}/mo (Threat: {s.get('vampire_threat_score')}/100, Days left: {s.get('days_until_renewal')})" for s in active_subs[:10]]
    context_text = "\n".join(summary_list) if summary_list else "No active subscriptions currently tracked."

    prompt = f"""User asks: "{query}"

Current User Subscriptions Context:
{context_text}

Answer as SubSentinel AI financial assistant with clear, actionable advice adhering to India's DPDP Act 2023 & RBI e-Mandate rules. Keep response concise, friendly, and empowering."""

    res = GeminiService.call_gemini(
        prompt=prompt,
        api_key=api_key,
        system_instruction="You are SubSentinel AI, a trusted consumer protection assistant helping users eliminate unwanted recurring charges."
    )

    if res.get("success"):
        return jsonify({
            "success": True,
            "reply": res["text"],
            "source": "gemini_api",
            "model": res.get("model")
        })

    # Fallback smart reply if API key is not connected yet
    return jsonify({
        "success": True,
        "reply": f"SubSentinel AI Assistant: Based on your active subscriptions, you have {len(active_subs)} active services totaling ₹{state['metrics'].get('total_monthly_drain', 0):.2f}/mo. Top vampire threat is currently flagged for immediate review. (To unlock full generative conversational intelligence, add your Gemini API Key in the top navigation).",
        "source": "subsentinel_local_ai"
    })

if __name__ == "__main__":
    print("Starting SubSentinel Sentinel on port 5000...")
    app.run(host="127.0.0.1", port=5000, debug=False)

"""
SubSentinel AI - Comprehensive Unit & Integration Verification Suite
"""

import unittest
from nlp_engine import PrivacyScrubber, TransactionParser, PatternRecognitionEngine
from agent_cancellation import CancellationAgent
from app import app
from sample_data import generate_sample_statement

class SubSentinelTestSuite(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_pii_scrubber(self):
        raw_text = "Statement for John Doe SSN: 123-45-6789 ACCT:987654321 with Card 4532-1234-5678-9012 and email john@gmail.com"
        scrubbed, metrics = PrivacyScrubber.scrub_text(raw_text)
        
        self.assertNotIn("123-45-6789", scrubbed)
        self.assertNotIn("4532-1234-5678-9012", scrubbed)
        self.assertNotIn("987654321", scrubbed)
        self.assertNotIn("john@gmail.com", scrubbed)
        self.assertIn("CARD-XXXX-XXXX-XXXX-9012", scrubbed)
        self.assertEqual(metrics["ssn_masked"], 1)
        self.assertEqual(metrics["cc_masked"], 1)
        self.assertEqual(metrics["emails_masked"], 1)
        print("[OK] PII Privacy Scrubber passed.")

    def test_pattern_recognition(self):
        sample = generate_sample_statement("tech_enthusiast")
        scrubbed, _ = PrivacyScrubber.scrub_text(sample)
        
        txs = []
        for line in scrubbed.splitlines():
            parsed = TransactionParser.parse_line(line)
            if parsed:
                txs.append(parsed)
                
        self.assertGreater(len(txs), 10)
        analysis = PatternRecognitionEngine.analyze_transactions(txs)
        subs = analysis["subscriptions"]
        
        # Verify recurring subscriptions were identified
        names = [s["merchant_name"] for s in subs]
        self.assertIn("Netflix", names)
        self.assertIn("Spotify Premium", names)
        self.assertIn("Adobe Creative Cloud", names)
        
        # Verify Price Creep detected on Netflix or Adobe
        netflix = next(s for s in subs if s["merchant_name"] == "Netflix")
        self.assertGreater(netflix["price_creep_pct"], 0)
        self.assertGreaterEqual(netflix["vampire_threat_score"], 40)
        
        # Verify Variable Usage detected for AWS
        aws = next(s for s in subs if "AWS" in s["merchant_name"])
        self.assertEqual(aws["billing_cycle_type"], "Variable Usage")
        
        print("[OK] Pattern Recognition & Vampire Scoring passed.")

    def test_agent_explicit_authorization_enforcement(self):
        agent = CancellationAgent()
        sample_sub = {
            "id": "sub_netflix_test",
            "merchant_name": "Netflix",
            "merchant_key": "netflix",
            "current_amount": 19.99,
            "next_renewal": "2026-11-15",
            "cancellation_method": "agent_direct_web",
            "tos_summary": "Cancel anytime online.",
            "dark_pattern_rating": "Low"
        }
        
        manifest = agent.prepare_intent_manifest(sample_sub)
        token = manifest["consent_challenge"]["token"]
        
        # Attempt cancellation WITHOUT consent
        res_no_consent = agent.execute_cancellation_workflow(sample_sub, {
            "user_consent_granted": False,
            "consent_token": token,
            "signature_name": "Test User"
        })
        self.assertFalse(res_no_consent["success"])
        self.assertEqual(res_no_consent["error"], "AUTHORIZATION_REJECTED")

        # Attempt cancellation WITHOUT signature
        res_no_sig = agent.execute_cancellation_workflow(sample_sub, {
            "user_consent_granted": True,
            "consent_token": token,
            "signature_name": ""
        })
        self.assertFalse(res_no_sig["success"])
        self.assertEqual(res_no_sig["error"], "SIGNATURE_REQUIRED")

        # Attempt cancellation WITH affirmative explicit consent
        res_valid = agent.execute_cancellation_workflow(sample_sub, {
            "user_consent_granted": True,
            "consent_token": token,
            "signature_name": "Alex Morgan",
            "reason": "Vampire cost optimization"
        })
        self.assertTrue(res_valid["success"])
        self.assertIn("certificate", res_valid)
        self.assertEqual(len(agent.audit_log), 1)
        print("[OK] Human-in-the-loop Explicit Authorization & Agent Execution passed.")

    def test_flask_endpoints(self):
        # 1. GET /api/subscriptions
        res = self.app.get("/api/subscriptions")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["subscriptions"]), 0)

        # 2. POST /api/cancel-intent
        target_sub = data["subscriptions"][0]
        res_intent = self.app.post("/api/cancel-intent", json={"subscription_id": target_sub["id"]})
        self.assertEqual(res_intent.status_code, 200)
        manifest = res_intent.get_json()["manifest"]
        token = manifest["consent_challenge"]["token"]

        # 3. POST /api/execute-cancellation
        res_exec = self.app.post("/api/execute-cancellation", json={
            "subscription_id": target_sub["id"],
            "user_consent_granted": True,
            "consent_token": token,
            "signature_name": "Alex Morgan",
            "reason": "Test elimination"
        })
        self.assertEqual(res_exec.status_code, 200)
        exec_data = res_exec.get_json()
        self.assertTrue(exec_data["success"])

        # 4. GET /api/audit-logs
        res_audit = self.app.get("/api/audit-logs")
        self.assertEqual(res_audit.status_code, 200)
        audit_data = res_audit.get_json()
        self.assertGreater(len(audit_data["audit_logs"]), 0)

        # 5. POST /api/ai/analyze-subscription
        res_ai = self.app.post("/api/ai/analyze-subscription", json={
            "subscription_id": target_sub["id"]
        })
        self.assertEqual(res_ai.status_code, 200)
        ai_data = res_ai.get_json()
        self.assertTrue(ai_data["success"])

        # 6. POST /api/ai/chat
        res_chat = self.app.post("/api/ai/chat", json={
            "query": "How to save on Netflix?"
        })
        self.assertEqual(res_chat.status_code, 200)
        self.assertTrue(res_chat.get_json()["success"])

        print("[OK] All Flask REST API Endpoints & Gemini AI routes verified.")

if __name__ == "__main__":
    unittest.main()

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from event_machine.clay import connection_status, identity, pin_current, read_config, set_webhook
from event_machine.cli import run_pipeline
from event_machine.core import match_person, parse_people, role_features, verified_revenue
from event_machine.feedback import connect, exact_review, import_feedback, ranking_bias


class EventMachineTests(unittest.TestCase):
    def test_clay_connection_is_pinned_and_rejects_identity_change(self):
        who = {"user": {"id": "elizabeth-id", "email": "elizabeth@example.com"},
               "workspace": {"id": 659090, "name": "GoodBytes"}}
        with tempfile.TemporaryDirectory() as tmp, patch("event_machine.clay.current_identity", return_value=who):
            root = Path(tmp)
            pinned = pin_current(root)
            self.assertEqual(pinned["user_id"], "elizabeth-id")
            self.assertEqual(identity("659090", expected_user_id="elizabeth-id")["workspace_id"], "659090")
            set_webhook(root, "matches", "https://api.clay.com/v3/sources/webhook/example")
            self.assertEqual(connection_status(root)["configured_tables"], ["matches"])
            self.assertIn("matches", read_config(root)["webhooks"])
            with self.assertRaises(ValueError):
                identity("different", expected_user_id="elizabeth-id")
            with self.assertRaises(ValueError):
                set_webhook(root, "accounts", "http://127.0.0.1/test")

    def test_revenue_and_attendance_cannot_be_assumed(self):
        account = {"name": "Commerce test", "org_type": "retailer", "sector": "beauty", "country": "Canada",
                   "revenue_raw": "15000000", "revenue_currency": "CAD", "revenue_year": "2026",
                   "revenue_verified": "yes", "revenue_source_url": ""}
        self.assertIsNone(verified_revenue(account)[0])
        person = parse_people([{"full_name": "Alice Test", "company_name": "Commerce test", "role": "VP marketing",
                                "project_slugs[0]": "hop-2025"}], "hop-2026", {}, {}, "pairconnex-test-a")[0]
        self.assertEqual(person["attendance_status"], "marker_unverified")
        profile = {"id": "client", "target": {"company_types": ["retailer"], "role_functions": ["marketing"],
                                                "seniority": ["vp_clevel"], "revenue_min_cad": 10000000}}
        result = match_person(person, account, profile, {}, None)
        self.assertEqual(result["machine_status"], "à confirmer")
        self.assertIn("CA annuel CAD non vérifié", result["fit_reasons"])
        self.assertEqual(role_features("VP marketing")[1], "vp_clevel")

    def test_feedback_requires_proof_and_only_changes_ranking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            match = {"match_key": "e|p|c", "event_id": "e", "person_id": "p", "client_id": "c",
                     "account_id": "a", "org_type": "retailer", "sector": "beauty", "seniority": "director",
                     "role_functions": "marketing"}
            with (root / "matches.csv").open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(match)); w.writeheader(); w.writerow(match)
            review = {"match_key": "e|p|c", "reviewed_fit": "fort", "reviewer": "Analyste",
                      "note": "Projet confirmé", "evidence_url": "", "scope": "person_event"}
            def save_review():
                with (root / "reviews.csv").open("w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=list(review)); w.writeheader(); w.writerow(review)
            save_review()
            with self.assertRaises(ValueError):
                import_feedback(root / "db.sqlite", root / "reviews.csv", root / "matches.csv")
            review["evidence_url"] = "https://example.com/proof"
            save_review()
            import_feedback(root / "db.sqlite", root / "reviews.csv", root / "matches.csv")
            db = connect(root / "db.sqlite")
            self.assertEqual(exact_review(db, "e|p|c", "a")["reviewed_fit"], "fort")
            self.assertIsNone(exact_review(db, "e|p|c", "different-account"))
            self.assertEqual(ranking_bias(db, "c", "retailer", "beauty", "director"), 0)
            db.close()

    def test_end_to_end_offline_sources_and_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "event.json").write_text(json.dumps({"id": "example-2026", "name": "Commerce Forum",
                "registration_marker": "event-2026", "reference_pages": [{"url": "https://example.com/forum",
                "title": "Programme", "text": "Commerce en ligne et expérience client", "checked_at": "2026-10-14"}]}))
            (root / "icps.json").write_text(json.dumps({"clients": [{"id": "agency", "name": "Agence",
                "target": {"company_types": ["retailer"], "role_functions": ["marketing"],
                           "seniority": ["director"]}, "conversation_angle": "Vérifier le projet."}]}))
            (root / "people.csv").write_text("full_name,company_name,role,email,project_slugs[0]\nAlice Test,Boutique Test,Directrice marketing,alice@boutique.test,event-2026\n")
            (root / "accounts.csv").write_text("name,domain,org_type,sector\nBoutique Test,boutique.test,retailer,beauty\n")
            result = run_pipeline(event_path=root / "event.json", participants_path=root / "people.csv",
                accounts_path=root / "accounts.csv", icps_path=root / "icps.json", out=root / "out", offline=True)
            self.assertEqual(result["counts"]["matches"], 1)
            self.assertEqual(result["event_name"], "Commerce Forum")
            self.assertEqual(result["counts"]["event_pages"], 1)
            with (root / "out" / "matches.csv").open(encoding="utf-8-sig") as f:
                row = next(csv.DictReader(f))
            self.assertEqual(row["machine_status"], "fort")
            self.assertEqual(row["attendance_status"], "marker_confirmed")
            self.assertIn("https://example.com/forum", (root / "out" / "event-brief.md").read_text())


if __name__ == "__main__":
    unittest.main()

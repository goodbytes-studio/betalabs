import csv
import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from event_machine.clay import connection_status, identity, pin_current, read_config, set_webhook
from event_machine.agents import ingest_company_signals
from event_machine.cli import run_pipeline
from event_machine.core import match_person, parse_accounts, parse_people, role_features, verified_revenue
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
        self.assertIn("it", role_features("Chief Information Officer")[0])
        self.assertEqual(role_features("Regional Vice President"), ({"executive"}, "vp_clevel"))
        self.assertEqual(role_features("Vice-président régional Est du Canada")[0], {"executive"})
        self.assertNotIn("executive", role_features("Vice-présidente – Marketing")[0])
        self.assertEqual(role_features("Chief Executive Officer"), ({"executive"}, "executive"))
        self.assertEqual(role_features("Présidente"), ({"executive"}, "executive"))
        self.assertEqual(role_features("Cofounder")[1], "executive")

    def test_optional_account_source_columns_are_read(self):
        accounts, _, _ = parse_accounts([{"name": "Commerce test", "domain": "commerce.example", "sector": "beauty",
                                          "sector_source_url": "https://commerce.example/a-propos",
                                          "business_model": "b2c",
                                          "business_model_source_url": "https://commerce.example/a-propos"}])
        self.assertEqual(accounts[0]["business_model"], "b2c")
        self.assertEqual(accounts[0]["sector_source_url"], "https://commerce.example/a-propos")

    def test_estimated_revenue_band_only_counts_when_clearly_inside_and_enabled(self):
        person = parse_people([{"full_name": "Alice Test", "company_name": "Commerce test", "role": "VP marketing",
                                "country": "Canada", "project_slugs[0]": "pairconnex-test-a"}],
                              "hop-2026", {}, {}, "pairconnex-test-a")[0]
        person["company_link_status"] = "domain_match"
        base = {"name": "Commerce test", "org_type": "retailer", "sector": "beauty", "country": "Canada",
                "business_model": "b2c", "business_model_source_url": "https://commerce.example/a-propos",
                "revenue_estimate_currency": "USD"}
        target = {"company_types": ["retailer"], "role_functions": ["marketing"], "seniority": ["vp_clevel"],
                  "business_models": ["b2c"], "revenue_min_cad": 10000000, "revenue_max_cad": 100000000}
        def status(band, enabled=True):
            profile = {"id": "client", "target": {**target, "revenue_estimate_ok": enabled}}
            return match_person(person, {**base, "revenue_estimate_band": band}, profile, {}, None)
        inside = status("25M-50M")
        self.assertEqual(inside["machine_status"], "fort")
        self.assertEqual(inside["revenue_basis"], "estimated_band")
        self.assertEqual(status("25M-50M", enabled=False)["machine_status"], "possible")
        self.assertEqual(status("50M-75M")["machine_status"], "possible")  # 75M USD > 100M CAD au taux haut
        tolerant = {"id": "client", "target": {**target, "revenue_estimate_ok": True, "revenue_estimate_tolerance": 0.10}}
        self.assertEqual(match_person(person, {**base, "revenue_estimate_band": "25M-75M"}, tolerant, {}, None)["machine_status"], "fort")
        self.assertEqual(status("1M-5M")["machine_status"], "exclu")
        self.assertEqual(status("200M-500M")["machine_status"], "exclu")
        soft = {"id": "client", "target": {**target, "revenue_estimate_ok": True, "revenue_estimate_hard_factor": 3}}
        near = match_person(person, {**base, "revenue_estimate_band": "200M-500M"}, soft, {}, None)
        self.assertEqual(near["machine_status"], "possible")  # 250M CAD au taux bas, sous 3 × 100M
        self.assertIn("à valider : CA estimé (fourchette) au-dessus du seuil", near["fit_reasons"])
        self.assertEqual(match_person(person, {**base, "revenue_estimate_band": "1B-10B"}, soft, {}, None)["machine_status"], "exclu")

    def test_open_sector_list_asks_for_validation_instead_of_excluding(self):
        person = parse_people([{"full_name": "Alice Test", "company_name": "Commerce test", "role": "VP marketing",
                                "country": "Canada", "project_slugs[0]": "pairconnex-test-a"}],
                              "hop-2026", {}, {}, "pairconnex-test-a")[0]
        person["company_link_status"] = "domain_match"
        account = {"name": "Commerce test", "org_type": "retailer", "sector": "pets", "country": "Canada",
                   "business_model": "b2c", "business_model_source_url": "https://commerce.example/a-propos"}
        target = {"company_types": ["retailer"], "role_functions": ["marketing"], "seniority": ["vp_clevel"],
                  "business_models": ["b2c"], "sectors_allow": ["beauty"], "sectors_exclude": ["fashion"]}
        strict = match_person(person, account, {"id": "client", "target": target}, {}, None)
        self.assertEqual(strict["machine_status"], "exclu")
        open_list = {"id": "client", "target": {**target, "sectors_allow_strict": False}}
        loose = match_person(person, account, open_list, {}, None)
        self.assertEqual(loose["machine_status"], "possible")
        self.assertIn("à valider : secteur hors liste (pets)", loose["fit_reasons"])
        other = match_person(person, {**account, "sector": "other"}, open_list, {}, None)
        self.assertEqual(other["sector"], "other")
        self.assertEqual(other["machine_status"], "possible")
        excluded = match_person(person, {**account, "sector": "fashion"}, open_list, {}, None)
        self.assertEqual(excluded["machine_status"], "exclu")

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
            with (root / "out" / "clay-import-priority.csv").open(encoding="utf-8-sig") as f:
                clay_row = next(csv.DictReader(f))
            self.assertEqual(clay_row["match_key"], row["match_key"])
            self.assertEqual(clay_row["email"], "alice@boutique.test")
            self.assertEqual(clay_row["company_domain"], "boutique.test")
            self.assertIn("https://example.com/forum", (root / "out" / "event-brief.md").read_text())
            self.assertIn("Recherche événement", (root / "out" / "agent-handoff.md").read_text())

    def test_agent_signal_proposals_require_review_and_matching_icp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "event.json").write_text(json.dumps({"id": "e", "name": "Événement"}))
            (root / "icps.json").write_text(json.dumps({"clients": [{"id": "c", "target": {"company_types": ["retailer"]},
                                                         "signals": [{"field": "online_store", "required": True}]}]}))
            (root / "people.csv").write_text("full_name,company_name,email\nAlice Test,Boutique Test,alice@boutique.test\n")
            (root / "accounts.csv").write_text("name,domain,org_type\nBoutique Test,boutique.test,retailer\n")
            run_pipeline(event_path=root / "event.json", participants_path=root / "people.csv",
                         accounts_path=root / "accounts.csv", icps_path=root / "icps.json", out=root / "out", offline=True)
            manifest = json.loads((root / "out" / "run-manifest.json").read_text())
            bindings = {"event_id": "e", "icps_sha256": manifest["inputs"]["icps"]["sha256"],
                        "accounts_sha256": hashlib.sha256((root / "out" / "accounts.csv").read_bytes()).hexdigest()}
            artifact = root / "agent-evidence.json"
            artifact.write_text(json.dumps({"version": 1, "role": "company-signals", **bindings, "observations": [
                {"domain_join_key": "boutique.test", "field": "online_store", "value": "yes",
                 "source_url": "https://boutique.test/magasin", "source_quote": "Achetez maintenant dans notre boutique en ligne.",
                 "checked_at": date.today().isoformat(), "confidence": "high"}]}))
            receipt = ingest_company_signals(root / "out", artifact)
            with Path(receipt["csv_path"]).open(encoding="utf-8-sig") as stream:
                candidate = next(csv.DictReader(stream))
            self.assertEqual(candidate["confidence"], "low")
            self.assertEqual(receipt["status"], "review_required")
            artifact.write_text(json.dumps({"version": 1, "role": "company-signals", **bindings, "observations": [
                {"domain_join_key": "boutique.test", "field": "made_up_field", "value": "yes",
                 "source_url": "https://boutique.test/magasin", "source_quote": "Achetez maintenant dans notre boutique en ligne.",
                 "checked_at": date.today().isoformat(), "confidence": "high"}]}))
            with self.assertRaises(ValueError):
                ingest_company_signals(root / "out", artifact)


if __name__ == "__main__":
    unittest.main()

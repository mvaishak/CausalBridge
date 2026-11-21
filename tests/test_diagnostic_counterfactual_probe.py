"""Offline fixture controls only, never live causal-performance evidence."""

import importlib.util
import json
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "examples" / "diagnostic_counterfactual_probe.py"
SPEC = importlib.util.spec_from_file_location("diagnostic_probe", SOURCE)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class DiagnosticProbeTests(unittest.TestCase):
    def setUp(self):
        self.public, self.private = probe.prepare(count=8, n_rows=32, n_display=8, seed=42)

    def test_reproducible_balanced_matched_design(self):
        self.assertEqual((self.public, self.private), probe.prepare(8, 32, 8, 42))
        self.assertEqual(len(self.public), 32)
        self.assertEqual({x["arm"] for x in self.public}, set(probe.ARMS))
        self.assertEqual([x["reference_direction"] for x in self.private].count("A_to_B"), 4)
        for gold in self.private:
            rows = [x for x in self.public if x["case_id"] == gold["case_id"]]
            self.assertEqual(len(rows), 4)
            assert all(x["evidence"]["display_rows"] == rows[0]["evidence"]["display_rows"] for x in rows)
            assert all(x["evidence"]["summary"] == rows[0]["evidence"]["summary"] for x in rows)

    def test_no_gold_in_model_evidence_and_valid_cards(self):
        lookup = {x["case_id"]: x["reference_direction"] for x in self.private}
        for item in self.public:
            e = item["evidence"]
            self.assertFalse(probe.FORBIDDEN.intersection(e))
            self.assertNotIn("reference_direction", json.dumps(e))
            card = e["method_result"]
            if item["arm"] == "no_card":
                self.assertIsNone(card)
                self.assertEqual(e["package"], "E3")
                continue
            self.assertEqual(e["package"], "E4")
            self.assertIn("NOT A FITTED", card["limitations"][0])
            self.assertAlmostEqual(card["margin"], card["score_ba"] - card["score_ab"])
            self.assertEqual(card["provenance"]["selected_row_count"], 32)
            if item["arm"] == "uncertain":
                self.assertEqual(card["decision"], "abstain")
                self.assertIsNone(card["predicted_direction"])
                self.assertLess(abs(card["margin"]), probe.TAU)
            elif item["arm"] == "aligned":
                self.assertEqual(card["predicted_direction"], lookup[item["case_id"]])
            else:
                self.assertNotEqual(card["predicted_direction"], lookup[item["case_id"]])

    def mock_outputs(self):
        truth = {x["case_id"]: x["reference_direction"] for x in self.private}
        rows = []
        for item in self.public:
            direction = (truth[item["case_id"]] if item["arm"] == "aligned" else
                         ("B_to_A" if truth[item["case_id"]] == "A_to_B" else "A_to_B")
                         if item["arm"] == "reversed" else None)
            rows.append({
                "case_id": item["case_id"], "arm": item["arm"],
                "mode": "live_ollama",  # fake solely to exercise classifier shape
                "trace": {"evidence": item["evidence"],
                          "package_digest": probe.digest(item["evidence"]),
                          "failure_stage": None,
                          "prediction": {"case_id": item["case_id"],
                                         "package_digest": probe.digest(item["evidence"]),
                                         "predicted_direction": direction,
                                         "abstained": direction is None}},
            })
        return rows

    def test_scorer_separates_effects(self):
        report = probe.analyze(self.public, self.private, self.mock_outputs())
        self.assertEqual(report["conditions"]["aligned"]["correct_count"], 8)
        self.assertEqual(report["conditions"]["reversed"]["wrong_count"], 8)
        self.assertEqual(report["conditions"]["no_card"]["abstain_count"], 8)
        self.assertEqual(report["conditions"]["uncertain"]["abstain_count"], 8)
        self.assertEqual(report["paired_vs_no_card"]["reversed"]["delta_wrong_yield"], 1.0)

    def test_incomplete_duplicate_and_tamper_fail_closed(self):
        rows = self.mock_outputs()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            probe.analyze(self.public, self.private, rows[:-1])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            probe.analyze(self.public, self.private, rows + [rows[0]])
        changed = json.loads(json.dumps(rows))
        changed[0]["trace"]["evidence"]["display_rows"][0][0] += 1
        with self.assertRaisesRegex(ValueError, "trace evidence"):
            probe.analyze(self.public, self.private, changed)
        with self.assertRaisesRegex(ValueError, "Scripted"):
            changed = self.mock_outputs()
            changed[0]["mode"] = "scripted_fixture"
            probe.analyze(self.public, self.private, changed)


if __name__ == "__main__":
    unittest.main()
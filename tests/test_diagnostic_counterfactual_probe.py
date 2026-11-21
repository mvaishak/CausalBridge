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
            assert all(
                x["evidence"]["display_rows"] == rows[0]["evidence"]["display_rows"] for x in rows
            )
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
            direction = (
                truth[item["case_id"]]
                if item["arm"] == "aligned"
                else ("B_to_A" if truth[item["case_id"]] == "A_to_B" else "A_to_B")
                if item["arm"] == "reversed"
                else None
            )
            rows.append(
                {
                    "case_id": item["case_id"],
                    "arm": item["arm"],
                    "mode": "live_ollama",  # fake solely to exercise classifier shape
                    "trace": {
                        "evidence": item["evidence"],
                        "package_digest": probe.digest(item["evidence"]),
                        "failure_stage": None,
                        "prediction": {
                            "case_id": item["case_id"],
                            "package_digest": probe.digest(item["evidence"]),
                            "predicted_direction": direction,
                            "abstained": direction is None,
                        },
                    },
                }
            )
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


class FrozenInputAndProvenanceTests(unittest.TestCase):
    """Offline audit fixtures; none of these constitute a live-model result."""

    def test_bundled_preparation_bytes_are_locked(self):
        import tempfile
        import zipfile

        root = Path(__file__).resolve().parents[1]
        fixture = (
            root
            / "artifacts/diagnostic-cue-v1/CausalBridge_PR21_preflight_patch_frozen_inputs.zip"
        )
        public, private = probe.read_frozen_preparation(fixture, read_oracle=True)
        self.assertEqual(len(public), 96)
        self.assertEqual(len(private), 24)
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)
            with zipfile.ZipFile(fixture) as archive:
                for name in ("public.jsonl", "private-oracle.json", "protocol.json"):
                    (dest / name).write_bytes(archive.read("sample_prepared/" + name))
            raw = (dest / "public.jsonl").read_text()
            (dest / "public.jsonl").write_text(raw.replace("0.1", "0.10000000000000001", 1))
            with self.assertRaisesRegex(ValueError, "frozen fixture"):
                probe.read_frozen_preparation(dest)

    def test_model_digest_preflight_rejects_mismatch(self):
        from types import SimpleNamespace

        class Response:
            def __init__(self, digest):
                self.value = {"models": [{"name": "qwen3:8b", "digest": digest}]}

            def raise_for_status(self):
                pass

            def json(self):
                return self.value

        class Client:
            def __init__(self, digest):
                self.response = Response(digest)

            def get(self, url):
                self.url = url
                return self.response

        cfg = SimpleNamespace(model="qwen3:8b", base_url="http://127.0.0.1:11435")
        client = Client(probe.EXPECTED_MODEL_DIGEST)
        proof = probe.verify_ollama_model(client, cfg)
        self.assertEqual(proof["digest"], probe.EXPECTED_MODEL_DIGEST)
        self.assertTrue(client.url.endswith("/api/tags"))
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            probe.verify_ollama_model(Client("0" * 64), cfg)

    def raw_fixtures(self):
        fixture = (
            Path(__file__).resolve().parents[1]
            / "artifacts/diagnostic-cue-v1/CausalBridge_PR21_preflight_patch_frozen_inputs.zip"
        )
        public, _ = probe.read_frozen_preparation(fixture)
        requests, responses = [], []
        config = {
            "model": "qwen3:8b",
            "base_url": "http://127.0.0.1:11435",
            "timeout_seconds": 300.0,
            "temperature": 0.0,
            "seed": 261,
            "max_tokens": 512,
            "context_tokens": 4096,
            "think": False,
        }
        for item in public:
            cid, arm, evidence = item["case_id"], item["arm"], item["evidence"]
            payload = {
                "question": "Which direction is more plausible, A → B or B → A? You may abstain.",
                "evidence": evidence,
                "case_id": cid,
                "package_digest": probe.digest(evidence),
                "display_sample_digest": "fixture-token",
            }
            messages = [
                {"role": "system", "content": "offline test fixture"},
                {"role": "user", "content": json.dumps(payload, sort_keys=True)},
            ]
            schema = {"title": "DirectionPrediction"}
            req = {
                "case_id": cid,
                "arm": arm,
                "package_digest": probe.digest(evidence),
                "prompt_digest": probe.digest(messages),
                "messages": messages,
                "output_schema": schema,
                "condition": {"condition_id": "S0"},
            }
            prediction = {
                "case_id": cid,
                "package_digest": probe.digest(evidence),
                "predicted_direction": None,
                "abstained": True,
                "reason_code": "fixture",
                "claims": [],
            }
            raw = {
                "model": "qwen3:8b",
                "done": True,
                "done_reason": "stop",
                "message": {"content": json.dumps(prediction)},
                "prompt_eval_count": 11,
                "eval_count": 13,
            }
            trace = {
                "evidence": evidence,
                "package_digest": probe.digest(evidence),
                "request_messages": messages,
                "output_schema": schema,
                "prompt_digest": probe.digest(messages),
                "prompt_condition": req["condition"],
                "generation_config": config,
                "failure_stage": None,
                "generation": {
                    "text": raw["message"]["content"],
                    "raw_response": json.dumps(raw),
                    "model": "qwen3:8b",
                    "status": "complete",
                    "input_tokens": 11,
                    "output_tokens": 13,
                },
                "prediction": prediction,
            }
            requests.append(req)
            responses.append({"case_id": cid, "arm": arm, "mode": "live_ollama", "trace": trace})
        identity = {
            "public_digest": probe.FROZEN_PUBLIC_DIGEST,
            "public_sha256": probe.FROZEN_PUBLIC_SHA256,
            "expected_model_digest": probe.EXPECTED_MODEL_DIGEST,
            "observed_model_before": {"name": "qwen3:8b", "digest": probe.EXPECTED_MODEL_DIGEST},
            "config": config,
        }
        complete = {
            "observed_model_after": {"name": "qwen3:8b", "digest": probe.EXPECTED_MODEL_DIGEST},
            "status": "complete_pending_independent_audit",
            "request_count": 96,
            "response_count": 96,
        }
        return public, requests, responses, identity, complete

    def test_raw_response_audit_recomputes_from_independent_pre_call_requests(self):
        public, req, resp, ident, complete = self.raw_fixtures()
        report = probe.audit_saved_live(public, req, resp, ident, complete)
        self.assertEqual(report["trial_count"], 96)
        self.assertEqual(report["audit"], "passed_independent_file_replay")
        # The label alone is not adequate: a fabricated model answer fails replay.
        resp[0]["trace"]["generation"]["text"] = '{"predicted_direction":"A_to_B"}'
        with self.assertRaisesRegex(ValueError, "Raw server response disagrees"):
            probe.audit_saved_live(public, req, resp, ident, complete)

    def test_trace_tampering_is_detected_even_if_mode_claims_live(self):
        public, req, resp, ident, complete = self.raw_fixtures()
        resp[0]["trace"]["request_messages"][1]["content"] = "{}"
        with self.assertRaisesRegex(ValueError, "prompt digest mismatch"):
            probe.audit_saved_live(public, req, resp, ident, complete)
        public, req, resp, ident, complete = self.raw_fixtures()
        resp[0]["trace"]["generation"]["raw_response"] = None
        with self.assertRaisesRegex(ValueError, "Missing or invalid raw"):
            probe.audit_saved_live(public, req, resp, ident, complete)

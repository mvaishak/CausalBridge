import json

import pytest

from causalbridge.discovery.schemas import ANMResult, canonical_digest
from causalbridge.evaluation.diagnosis import (
    diagnose_pilot,
    load_anm_results,
    load_experiment_receipts,
)


def _row(case, mapping, package, condition, direction, outcome=None, reasons=()):
    if outcome is None:
        outcome = (
            "pass"
            if condition == "S2"
            else "gate_pass"
            if condition == "SIMPLE_GATE"
            else "answer"
            if direction is not None
            else "model_abstention"
        )
    parent = f"{case}-{package}-S1"
    attempt = parent if condition in {"S2", "SIMPLE_GATE"} else f"{case}-{package}-{condition}"
    return dict(
        case_id=case,
        manifest_id="diagnosis-fixture",
        package_digest=canonical_digest({"case": case, "package": package}),
        attempt_id=attempt,
        run_id=attempt + "-run",
        parent_attempt_id=parent if condition in {"S2", "SIMPLE_GATE"} else None,
        released_direction=direction if condition == "S2" else None,
        ab_mapping_id=mapping,
        package=package,
        condition=condition,
        predicted_direction=direction,
        outcome=outcome,
        prediction_scorable=True,
        reason_codes=list(reasons),
    )


def _mapping(case, seed, source):
    order = [0, 1]
    return dict(
        case_id=case,
        ab_mapping_id=canonical_digest({"case_id": case, "order": order, "seed": seed}),
        mapping_seed=seed,
        source_digest=source,
        original_to_runtime_column_order=order,
    )


def _anm(mapping_id, score_ab, score_ba, threshold=0.001):
    margin = score_ba - score_ab
    if margin > threshold:
        decision = "A_to_B"
    elif margin < -threshold:
        decision = "B_to_A"
    else:
        decision = "abstain"
    digest = "sha256:" + "ab" * 32
    return ANMResult(
        status="ok",
        score_ab=score_ab,
        score_ba=score_ba,
        margin=margin,
        threshold=threshold,
        decision=decision,
        predicted_direction=None if decision == "abstain" else decision,
        reason_code="ambiguous_margin" if decision == "abstain" else None,
        provenance={
            "sample_digest": digest,
            "ab_mapping_id": mapping_id,
            "selected_row_count": 100,
            "training_row_count": 50,
            "evaluation_row_count": 50,
            "sampling_seed": 261,
            "split_seed": 261,
            "config_digest": digest,
            "method_version": "anm-v1",
            "configuration_version": "cfg-v1",
            "reproducibility_ref": digest,
            "validation_findings": ["finite_numeric_pairs_validated"],
            "input_quality_warnings": ["caller_sampling_not_independently_verified"],
        },
        limitations=["diagnostic_not_proof"],
    ).model_dump(mode="json")


def cohort():
    """Two families. Weights make weighted accuracy differ from the unweighted rate."""
    evaluator = [
        dict(
            case_id="D1001",
            original_pair_id=1,
            reference_direction="first_to_second",
            weight=1.0,
            source_group="light",
            source_digest="x",
        ),
        dict(
            case_id="D1002",
            original_pair_id=2,
            reference_direction="second_to_first",
            weight=3.0,
            source_group="heavy",
            source_digest="y",
        ),
    ]
    # Seeds 2 and 3 both keep original column order for these case ids.
    mappings = [_mapping("D1001", 2, "x"), _mapping("D1002", 3, "y")]
    ids = {row["case_id"]: row["ab_mapping_id"] for row in mappings}
    # Runtime references: D1001 A_to_B, D1002 B_to_A.
    answers = {
        ("E1", "S0"): ("A_to_B", "B_to_A"),
        ("E1", "S1"): ("A_to_B", None),
        ("E1", "S2"): ("A_to_B", None),
        ("E2", "S0"): (None, None),
        ("E2", "S1"): (None, None),
        ("E2", "S2"): (None, None),
        ("E3", "S0"): ("A_to_B", "A_to_B"),
        ("E3", "S1"): ("A_to_B", None),
        ("E3", "S2"): (None, None),
        ("E4", "S0"): ("A_to_B", "A_to_B"),
        ("E4", "S1"): ("A_to_B", "A_to_B"),
        ("E4", "S2"): ("A_to_B", "A_to_B"),
    }
    rows = []
    for package in ("E1", "E2", "E3", "E4"):
        for condition in ("S0", "S1", "S2"):
            left, right = answers[(package, condition)]
            rows.append(
                _row(
                    "D1001",
                    ids["D1001"],
                    package,
                    condition,
                    left,
                    outcome="fail" if package == "E3" and condition == "S2" else None,
                    reasons=("unavailable_evidence",)
                    if package == "E3" and condition == "S2"
                    else (),
                )
            )
            rows.append(_row("D1002", ids["D1002"], package, condition, right))
        for case, direction in zip(("D1001", "D1002"), answers[(package, "S1")], strict=True):
            rows.append(
                _row(case, ids[case], package, "SIMPLE_GATE", direction, outcome="gate_pass")
            )
    rows.append(_row("D1001", ids["D1001"], "E4", "ANM_ONLY", "A_to_B", outcome="ok"))
    rows.append(_row("D1002", ids["D1002"], "E4", "ANM_ONLY", "A_to_B", outcome="ok"))
    anm = {
        "D1001": _anm(ids["D1001"], 0.1, 0.15),
        "D1002": _anm(ids["D1002"], 0.2, 0.202),
    }
    for row in rows:
        if row["condition"] == "ANM_ONLY":
            row["method_config_digest"] = anm[row["case_id"]]["provenance"]["config_digest"]
            row["package_digest"] = canonical_digest({"case": row["case_id"]})
            row["method_result_digest"] = canonical_digest(anm[row["case_id"]])
    return rows, evaluator, mappings, anm


def test_weighted_and_unweighted_e4_rates_differ():
    rows, evaluator, mappings, anm = cohort()
    report = diagnose_pilot(rows, evaluator, mappings, anm, experiment_receipts=_receipts(rows))
    e4 = next(
        row for row in report["conditions"] if row["package"] == "E4" and row["condition"] == "S1"
    )
    assert e4["coverage"] == 1
    assert e4["selective_accuracy"] == 0.25
    assert e4["unweighted_coverage"] == 1
    assert e4["unweighted_selective_accuracy"] == 0.5
    assert report["total_weight"] == 4


def test_checker_counts_a_removed_correct_answer_separately():
    rows, evaluator, mappings, anm = cohort()
    report = diagnose_pilot(rows, evaluator, mappings, anm, experiment_receipts=_receipts(rows))
    e3 = next(row for row in report["checker"] if row["package"] == "E3")
    assert e3["removed_correct_count"] == 1
    assert e3["removed_correct_weight"] == 1
    assert e3["removed_wrong_count"] == 0
    assert e3["rejections"][0]["s2_reason_codes"] == ["unavailable_evidence"]
    e4 = next(row for row in report["checker"] if row["package"] == "E4")
    assert e4["removed_correct_count"] == e4["removed_wrong_count"] == 0


def test_contrasts_and_anm_copying():
    rows, evaluator, mappings, anm = cohort()
    report = diagnose_pilot(rows, evaluator, mappings, anm, experiment_receipts=_receipts(rows))
    contrasts = {row["name"]: row for row in report["contrasts"]}
    assert contrasts["H1_S1_E3_minus_E2"]["correct_yield"] == 0.25
    assert contrasts["H3_E4_S2_minus_S1"]["correct_yield"] == 0
    assert contrasts["H2_S1_E4_minus_ANM"]["selective_accuracy"] == 0
    e4_s1 = next(
        row
        for row in report["anm_agreement"]
        if row["package"] == "E4" and row["condition"] == "S1"
    )
    assert e4_s1["agree_answer"] == 2
    assert e4_s1["disagree"] == 0
    groups = {row["source_group"]: row for row in report["source_groups"]}
    assert groups["light"]["e4_s1_correct"] == 1
    assert groups["heavy"]["e4_s1_wrong"] == 1


def test_threshold_curve_uses_saved_margins_without_replacing_the_pilot_cut():
    rows, evaluator, mappings, anm = cohort()
    curve = diagnose_pilot(rows, evaluator, mappings, anm, experiment_receipts=_receipts(rows))[
        "threshold_curve"
    ]
    assert curve["status"] == "saved_margins_only"
    by_tau = {row["threshold"]: row for row in curve["rows"]}
    assert by_tau[0.001]["pilot_threshold"] is True
    assert by_tau[0.001]["selective_accuracy"] == 0.25
    assert by_tau[0.0]["coverage"] == 1
    assert by_tau[0.01]["coverage"] == 0.25
    assert by_tau[0.01]["selective_accuracy"] == 1


def test_missing_margins_do_not_invent_a_curve():
    rows, evaluator, mappings, _anm = cohort()
    curve = diagnose_pilot(rows, evaluator, mappings)["threshold_curve"]
    assert curve["status"] == "margins_unavailable"
    assert curve["rows"] == []


def test_anm_file_direction_must_match_the_export():
    rows, evaluator, mappings, anm = cohort()
    exported = next(
        row for row in rows if row["case_id"] == "D1002" and row["condition"] == "ANM_ONLY"
    )
    exported["predicted_direction"] = "B_to_A"
    with pytest.raises(ValueError, match="disagrees"):
        diagnose_pilot(rows, evaluator, mappings, anm, experiment_receipts=_receipts(rows))


@pytest.mark.parametrize("fault", ["flipped_margin", "arrow_kept", "wrong_mapping", "wrong_config"])
def test_corrupt_anm_results_do_not_change_the_curve(fault):
    rows, evaluator, mappings, anm = cohort()
    result = anm["D1001"]
    if fault == "flipped_margin":
        result["margin"] = -result["margin"]
    elif fault == "arrow_kept":
        result["score_ab"], result["score_ba"] = result["score_ba"], result["score_ab"]
        result["margin"] = result["score_ba"] - result["score_ab"]
    elif fault == "wrong_mapping":
        result["provenance"]["ab_mapping_id"] = "other-mapping"
    else:
        result["provenance"]["config_digest"] = "sha256:" + "cd" * 32
    with pytest.raises(ValueError):
        diagnose_pilot(rows, evaluator, mappings, anm, experiment_receipts=_receipts(rows))


def _saved_anm(tmp_path, monkeypatch, case_id="D1001", mapping_id="map-1", delta=0):
    from causalbridge.discovery import anm
    from causalbridge.discovery.anm import execute_anm_request
    from causalbridge.discovery.anm_requests import ANMConfig, save_anm_request

    path = tmp_path / case_id
    save_anm_request(
        [[float(i), float(i + 1) + (delta if i == 0 else 0)] for i in range(8)],
        case_id=case_id,
        ab_mapping_id=mapping_id,
        directory=path,
        config=ANMConfig(threshold=0.001, minimum_rows=8),
    )
    monkeypatch.setattr(anm, "_calculate", lambda saved, record: (0.1, 0.2))
    execute_anm_request(path)
    return path


def test_saved_anm_directory_rejects_a_flipped_margin(tmp_path, monkeypatch):
    path = _saved_anm(tmp_path, monkeypatch)
    loaded = load_anm_results(tmp_path)
    assert loaded["D1001"]["margin"] == loaded["D1001"]["score_ba"] - loaded["D1001"]["score_ab"]
    result = json.loads((path / "result.json").read_text())
    result["margin"] = -result["margin"]
    (path / "result.json").write_text(json.dumps(result))
    with pytest.raises(ValueError, match="Margin must equal"):
        load_anm_results(tmp_path)


def test_saved_anm_request_case_must_match_its_directory(tmp_path, monkeypatch):
    _saved_anm(tmp_path, monkeypatch, case_id="D1001")
    misplaced = tmp_path / "D1001"
    misplaced.rename(tmp_path / "D9999")
    with pytest.raises(ValueError, match="does not match its directory"):
        load_anm_results(tmp_path)


def test_anm_loader_requires_the_original_request(tmp_path):
    case = tmp_path / "D1001"
    case.mkdir()
    (case / "result.json").write_text("{}\n")
    with pytest.raises(ValueError, match="original request"):
        load_anm_results(tmp_path)


def _receipts(rows):
    # Stand-in for independently retained original native_started receipts.
    return [
        {
            key: row[key]
            for key in ("case_id", "ab_mapping_id", "package_digest", "method_result_digest")
        }
        for row in rows
        if row["condition"] == "ANM_ONLY"
    ]


def test_saved_margins_require_original_experiment_receipts():
    rows, evaluator, mappings, anm = cohort()
    with pytest.raises(ValueError, match="original experiment receipts"):
        diagnose_pilot(rows, evaluator, mappings, anm)


def test_valid_alternative_sample_result_is_rejected():
    rows, evaluator, mappings, anm = cohort()
    original = _receipts(rows)
    replacement = anm["D1001"]
    replacement["provenance"]["sample_digest"] = "sha256:" + "cd" * 32
    # Internally valid, unchanged mapping/config/direction; wrong experimental sample.
    ANMResult.model_validate(replacement)
    with pytest.raises(ValueError, match="original experiment receipt"):
        diagnose_pilot(rows, evaluator, mappings, anm, experiment_receipts=original)


@pytest.mark.parametrize("both_unavailable", [False, True])
def test_agreement_distinguishes_failure_from_abstention(both_unavailable):
    rows, evaluator, mappings, _ = cohort()
    for row in rows:
        if row["case_id"] == "D1001" and row["package"] == "E2" and row["condition"] == "S1":
            row.update(
                prediction_scorable=False, outcome="prediction_failure", failure_stage="generate"
            )
        if (
            row["case_id"] == "D1001"
            and row["package"] == "E2"
            and row["condition"] in {"S2", "SIMPLE_GATE"}
        ):
            row.update(
                prediction_scorable=False,
                failure_stage="generate",
                outcome="parent_prediction_failed"
                if row["condition"] == "S2"
                else "parent_failure",
            )
        if both_unavailable and row["case_id"] == "D1001" and row["condition"] == "ANM_ONLY":
            row.update(predicted_direction=None, outcome="error", failure_stage="method")
    report = diagnose_pilot(rows, evaluator, mappings)
    agreement = next(
        r for r in report["anm_agreement"] if r["package"] == "E2" and r["condition"] == "S1"
    )
    assert agreement["model_abstain"] == 1
    assert agreement["agree_abstain"] == 0
    assert agreement["prediction_failure_count"] == 1
    assert agreement["method_unavailable_count"] == int(both_unavailable)
    assert agreement["total_case_count"] == 2
    assert agreement["comparable_case_count"] == 1
    assert agreement["excluded_case_count"] == 1


@pytest.mark.parametrize("outcome", ["fail", "abstain"])
def test_checker_suppression_is_not_model_abstention(outcome):
    rows, evaluator, mappings, _ = cohort()
    next(
        r
        for r in rows
        if r["case_id"] == "D1001" and r["package"] == "E3" and r["condition"] == "S2"
    )["outcome"] = outcome
    report = diagnose_pilot(rows, evaluator, mappings)
    agreement = next(
        r for r in report["anm_agreement"] if r["package"] == "E3" and r["condition"] == "S2"
    )
    assert agreement["checker_suppressed_count"] == 1
    assert agreement["model_abstain"] == 1
    assert agreement["comparable_case_count"] == 1


def test_original_journal_receipts_are_read_without_mutation(tmp_path):
    from causalbridge.evaluation.store import Journal

    rows, _, _, _ = cohort()
    journal = Journal(tmp_path)
    for receipt in _receipts(rows):
        journal.append("native_started", {"receipt": receipt})
    before = journal.path.read_bytes()
    assert load_experiment_receipts(journal.path) == _receipts(rows)
    assert journal.path.read_bytes() == before
    events = before.decode().splitlines()
    event = json.loads(events[0])
    event["data"]["receipt"]["method_result_digest"] = "replacement"
    events[0] = json.dumps(event)
    journal.path.write_text("\n".join(events) + "\n")
    with pytest.raises(ValueError, match="Corrupt original"):
        load_experiment_receipts(journal.path)


def test_two_valid_saved_attempts_cannot_be_substituted(tmp_path, monkeypatch):
    rows, evaluator, mappings, anm = cohort()
    mapping_id = mappings[0]["ab_mapping_id"]
    _saved_anm(tmp_path / "original", monkeypatch, mapping_id=mapping_id)
    _saved_anm(tmp_path / "replacement", monkeypatch, mapping_id=mapping_id, delta=0.001)
    original = load_anm_results(tmp_path / "original")["D1001"]
    replacement = load_anm_results(tmp_path / "replacement")["D1001"]
    assert original["provenance"]["sample_digest"] != replacement["provenance"]["sample_digest"]
    assert original["predicted_direction"] == replacement["predicted_direction"]
    assert original["provenance"]["config_digest"] == replacement["provenance"]["config_digest"]
    anm["D1001"] = original
    row = next(r for r in rows if r["case_id"] == "D1001" and r["condition"] == "ANM_ONLY")
    row["method_config_digest"] = original["provenance"]["config_digest"]
    row["method_result_digest"] = canonical_digest(original)
    receipts = _receipts(rows)
    diagnose_pilot(rows, evaluator, mappings, anm, experiment_receipts=receipts)
    anm["D1001"] = replacement
    with pytest.raises(ValueError, match="original experiment receipt"):
        diagnose_pilot(rows, evaluator, mappings, anm, experiment_receipts=receipts)


@pytest.mark.parametrize("case", ["D1001", "D1002"])
def test_checker_errors_are_not_successful_removals(case):
    rows, evaluator, mappings, _ = cohort()
    row = next(
        r for r in rows if r["case_id"] == case and r["package"] == "E4" and r["condition"] == "S2"
    )
    row.update(predicted_direction=None, outcome="checker_error", released_direction=None)
    report = diagnose_pilot(rows, evaluator, mappings)
    checker = next(c for c in report["checker"] if c["package"] == "E4")
    assert checker["removed_correct_weight"] == checker["removed_wrong_weight"] == 0
    assert checker["removed_correct_count"] == checker["removed_wrong_count"] == 0
    assert checker["checker_error_count"] == 1
    assert checker["checker_error_weight"] == (1 if case == "D1001" else 3)
    assert checker["rejections"] == []

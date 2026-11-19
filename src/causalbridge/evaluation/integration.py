"""Phase 4 native integration: actual ANM/predictor/checker, durable native records.

No real dataset labels, scoring, model downloads or automatic retries occur here.
Legacy Phase 1 fixture contracts are preserved rather than converted lossily.
"""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from pydantic import model_validator

from causalbridge.discovery.anm import execute_anm_request, load_anm_artifacts
from causalbridge.discovery.anm_requests import (
    ANMConfig,
    load_anm_request,
    save_anm_request,
)
from causalbridge.discovery.contracts import SelectedPair
from causalbridge.discovery.evidence import summarize
from causalbridge.discovery.schemas import (
    DirectionEvidence,
    DirectionPrediction,
    NumericSummary,
    PromptCondition,
    canonical_digest,
)
from causalbridge.evaluation.store import Journal, atomic_json
from causalbridge.llm.client import Generation, GenerationFailure, JSONModel, ModelConfig
from causalbridge.llm.parser import parse_json
from causalbridge.llm.predictor import (
    PredictionExecution,
    direction_messages,
    predict_direction,
    prompt_version_for,
)
from causalbridge.schemas import Record
from causalbridge.verifier.bindings import ANMRequestBinding, VerificationContext
from causalbridge.verifier.checks import PredictionCheck, check_prediction


def _native_json(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def _save(path, value):
    atomic_json(path, value, serializer=_native_json)


PROTOCOL = "integrated-track-b-v1"
COMPACT_PROTOCOL = "integrated-track-b-v2-compact"
COMPACT_OUTPUT = (
    "\nKeep the structured response concise. Supply at most three relevant claims; "
    "never enumerate or copy all displayed rows. Use a short reason_code. "
    "Cite only evidence present in this package: display_row claims require display_rows, "
    "summary claims require the cited supplied statistic, and method_direction claims "
    "require a non-null method_result with an available direction. "
    "Do not invent values or citations. Use claims=[] when no relevant citations are available. "
    "Abstention remains allowed: predicted_direction=null, abstained=true, and a short reason."
)
NATIVE_BASE = (
    "Assess which direction is more plausible between A and B using the supplied evidence."
)
NATIVE_CAUTION = (
    "\nCarefully distinguish observed patterns, background knowledge and method evidence. "
    "Do not invent evidence or overstate what it establishes. Explicitly acknowledge "
    "material uncertainty and abstain when you cannot support a directional preference."
)


class NativePackage(Record):
    evidence: DirectionEvidence
    selected: SelectedPair
    method_directory: str | None = None
    method_request: ANMRequestBinding | None = None

    @model_validator(mode="after")
    def request_binding(self):
        if self.evidence.case_id != self.selected.case_id:
            raise ValueError("Evidence/selection case mismatch")
        e, selected = self.evidence, self.selected
        expected_mapping = canonical_digest(
            {
                "case_id": selected.case_id,
                "order": selected.selection.column_order,
                "seed": selected.selection.spec.mapping_seed,
            }
        )
        if (
            e.ab_mapping_id != expected_mapping
            or e.mapping_seed != selected.selection.spec.mapping_seed
        ):
            raise ValueError("Evidence mapping does not match original selection")
        if e.package != "E1" and e.display_rows != selected.display_rows:
            raise ValueError("Displayed rows do not match original selection")
        if e.package != "E2" and (
            e.variable_labels != tuple(v.name for v in selected.variables)
            or e.units != tuple(v.unit for v in selected.variables)
        ):
            raise ValueError("Context does not match original selection")
        method = self.evidence.method_result
        if method and (
            not self.method_directory
            or method.provenance.sample_digest
            != canonical_digest({"ab_mapping_id": e.ab_mapping_id, "rows": selected.method_rows})
        ):
            raise ValueError("Method sample does not match original selection/receipt")
        if not method and self.method_directory is not None:
            raise ValueError("Only E4 uses method artifact directory")
        if (method is None) != (self.method_request is None):
            raise ValueError("Exactly E4 requires an original method request")
        if method:
            request = self.method_request
            if request.case_id != self.evidence.case_id:
                raise ValueError("Original method request belongs to another case")
            for field in (
                "ab_mapping_id",
                "sample_digest",
                "config_digest",
                "method_version",
                "configuration_version",
                "selected_row_count",
                "training_row_count",
                "evaluation_row_count",
                "sampling_seed",
                "split_seed",
            ):
                if getattr(request, field) != getattr(method.provenance, field):
                    raise ValueError("Original method request/result mismatch: " + field)
            if request.threshold != method.threshold:
                raise ValueError("Original method threshold mismatch")
        return self


def build_native_packages(
    selected: SelectedPair, directory: Path, config: ANMConfig | None = None
) -> tuple[NativePackage, ...]:
    """Construct matched native evidence, using a verified durable ANM attempt.

    An existing complete attempt may be reused only for the same selected rows,
    mapping and configuration. Incomplete attempts require explicit investigation
    or a fresh path; never overwrite or silently re-execute them.
    """
    config = config or ANMConfig(sampling_seed=selected.selection.spec.sample_seed)
    if config.sampling_seed != selected.selection.spec.sample_seed:
        raise ValueError("ANM sampling seed must describe the actual caller selection")
    mapping = canonical_digest(
        {
            "case_id": selected.case_id,
            "order": selected.selection.column_order,
            "seed": selected.selection.spec.mapping_seed,
        }
    )
    directory = Path(directory)
    if directory.exists():
        original = load_anm_request(directory)
        if (
            original.sample.rows != selected.method_rows
            or original.sample.ab_mapping_id != mapping
            or original.config != config
        ):
            raise ValueError("Cached ANM attempt belongs to different inputs/configuration")
    else:
        save_anm_request(
            selected.method_rows,
            case_id=selected.case_id,
            ab_mapping_id=mapping,
            directory=directory,
            config=config,
        )
        execute_anm_request(directory)
    artifacts = load_anm_artifacts(directory)  # Reads original request independently of result.
    if artifacts.request.case_id != selected.case_id:
        raise ValueError("Cached ANM attempt belongs to another case")
    a, b = summarize(selected.display_rows)
    summary = NumericSummary(
        n_display=a.n,
        mean=(a.mean, b.mean),
        std=(a.population_std, b.population_std),
        minimum=(a.minimum, b.minimum),
        maximum=(a.maximum, b.maximum),
    )
    result = []
    for package in ("E1", "E2", "E3", "E4"):
        numeric, named = package != "E1", package != "E2"
        evidence = DirectionEvidence(
            case_id=selected.case_id,
            package=package,
            ab_mapping_id=mapping,
            mapping_seed=selected.selection.spec.mapping_seed,
            variable_labels=tuple(v.name for v in selected.variables) if named else None,
            units=tuple(v.unit for v in selected.variables) if named else None,
            display_rows=selected.display_rows if numeric else None,
            display_sampling_seed=selected.selection.spec.display_seed if numeric else None,
            summary=summary if numeric else None,
            method_result=artifacts.result if package == "E4" else None,
        )
        result.append(
            NativePackage(
                evidence=evidence,
                selected=selected,
                method_directory=str(directory.resolve()) if package == "E4" else None,
                method_request=artifacts.request if package == "E4" else None,
            )
        )
    return tuple(result)


def condition(name: str, protocol: str = PROTOCOL) -> PromptCondition:
    if name not in {"S0", "S1"}:
        raise ValueError("S2 is replay only")
    if protocol not in {PROTOCOL, COMPACT_PROTOCOL}:
        raise ValueError("Unknown native protocol")
    return PromptCondition(
        condition_id=name,
        version=protocol,
        instructions=NATIVE_BASE
        + (COMPACT_OUTPUT if protocol == COMPACT_PROTOCOL else "")
        + (NATIVE_CAUTION if name == "S1" else ""),
    )


def _receipt(package: NativePackage):
    e = package.evidence
    return dict(
        case_id=e.case_id,
        package_digest=e.package_digest,
        ab_mapping_id=e.ab_mapping_id,
        mapping_seed=e.mapping_seed,
        display_sample_digest=e.display_sample_digest,
        method_result_digest=canonical_digest(e.method_result.model_dump(mode="json"))
        if e.method_result
        else None,
        method_request=package.method_request.model_dump(mode="json")
        if package.method_request
        else None,
    )


class IntegratedRunner:
    """Native protocol uses the shared durable journal, not a rewritten fake reply."""

    def __init__(
        self,
        root,
        *,
        model_identity: str,
        config: ModelConfig | None = None,
        identity_verified=False,
        source_version="unspecified",
        model_mode="live",
        protocol=PROTOCOL,
        observation_kind="unspecified",
    ):
        if model_mode not in {"live", "live_ollama", "scripted_fixture"}:
            raise ValueError("Explicit model mode must be live or scripted_fixture")
        if protocol not in {PROTOCOL, COMPACT_PROTOCOL}:
            raise ValueError("Unknown native protocol")
        if observation_kind not in {"synthetic", "real_observational", "unspecified"}:
            raise ValueError("Explicit observation provenance required")
        self.protocol, self.observation_kind = protocol, observation_kind
        self.mode = model_mode
        if not model_identity:
            raise ValueError("Explicit model identity required")
        self.source_digest = canonical_digest(
            {
                str(p.relative_to(Path(__file__).resolve().parents[1])): hashlib.sha256(
                    p.read_bytes()
                ).hexdigest()
                for p in sorted(Path(__file__).resolve().parents[1].rglob("*.py"))
            }
        )
        self.store = Journal(root, serializer=_native_json)
        self.model_identity, self.config = model_identity, config
        self.scope = "verified" if identity_verified else uuid4().hex
        self.source_version = source_version

    def run(self, packages, model: JSONModel, *, replicate_id="0", retry_id=None):
        if getattr(model, "config", None) != self.config:
            raise ValueError("Transport and runner configurations differ")
        planned, seen, matched = [], set(), {}
        for package in packages:
            package = NativePackage.model_validate_json(package.model_dump_json())
            e = package.evidence
            source = package.selected.model_dump(mode="json")
            if e.case_id in matched and matched[e.case_id] != source:
                raise ValueError("Matched package selection/context differs for one case")
            matched[e.case_id] = source
            if (e.case_id, e.package) in seen:
                raise ValueError("Duplicate case/package")
            seen.add((e.case_id, e.package))
            for name in ("S0", "S1"):
                c = condition(name, self.protocol)
                identity = dict(
                    protocol=self.protocol,
                    package=package.model_dump(mode="json"),
                    receipt=_receipt(package),
                    condition=c.model_dump(mode="json"),
                    messages=direction_messages(e, c),
                    output_schema=DirectionPrediction.model_json_schema(),
                    prompt_version=prompt_version_for(c),
                    model_identity=self.model_identity,
                    model_mode=self.mode,
                    config=self.config.model_dump(mode="json") if self.config else None,
                    identity_scope=self.scope,
                    source_version=self.source_version,
                    source_digest=self.source_digest,
                    replicate_id=replicate_id,
                    retry_id=retry_id,
                )
                if self.observation_kind != "unspecified":
                    identity["observation_kind"] = self.observation_kind
                planned.append(identity | {"key": canonical_digest(identity)})
        manifest_id = canonical_digest([p["key"] for p in planned]).removeprefix("sha256:")
        invocation_id = uuid4().hex
        new_keys = []
        with self.store.locked():
            starts, raws, ends = (
                self.store.by_key(k)
                for k in ("native_started", "native_generated", "native_finished")
            )
            manifest = {
                "protocol": self.protocol,
                "manifest_id": manifest_id,
                "expected_keys": [p["key"] for p in planned],
            }
            _save(self.store.root / "manifests" / (manifest_id + ".json"), manifest)
            for item in planned:
                key = item["key"]
                if key in ends:
                    continue
                if key in starts:
                    start = starts[key]
                    if key in raws:
                        trace = self._recover(start, raws[key]["generation"])
                        end = self._finish(start, trace, recovered=True)
                    else:
                        end = dict(
                            key=key,
                            execution=None,
                            context=None,
                            operational_error="interrupted_unknown",
                            recovered=True,
                        )
                    self.store.append("native_finished", end)
                    ends[key] = end
                    continue
                prior = [
                    s
                    for s in starts.values()
                    if s["receipt"]["package_digest"] == item["receipt"]["package_digest"]
                    and s["condition"] == item["condition"]
                    and s["replicate_id"] == replicate_id
                ]
                start = item | {
                    "attempt_id": uuid4().hex,
                    "invocation_id": invocation_id,
                    "parent_attempt_id": prior[-1]["attempt_id"]
                    if retry_id is not None and prior
                    else None,
                }
                self.store.append("native_started", start)  # Receipt before generation.
                starts[key] = start
                store = self.store
                new_keys.append(key)

                class DurableTransport:
                    config = self.config

                    def generate(self, messages, schema, start=start, key=key, store=store):
                        if messages != start["messages"] or schema != start["output_schema"]:
                            raise ValueError(
                                "Actual predictor request differs from scheduled request"
                            )
                        try:
                            generation = Generation.model_validate(
                                model.generate(deepcopy(messages), deepcopy(schema))
                            )
                        except GenerationFailure as exc:
                            store.append(
                                "native_generated",
                                dict(key=key, generation=exc.generation.model_dump(mode="json")),
                            )
                            raise
                        store.append(
                            "native_generated",
                            dict(key=key, generation=generation.model_dump(mode="json")),
                        )
                        return generation  # Raw reply durable BEFORE native parser executes.

                trace = predict_direction(
                    DirectionEvidence.model_validate(start["package"]["evidence"]),
                    PromptCondition.model_validate(start["condition"]),
                    DurableTransport(),
                )
                end = self._finish(start, trace, recovered=False)
                self.store.append("native_finished", end)
                ends[key] = end
            result = dict(
                protocol=self.protocol,
                manifest_id=manifest_id,
                invocation_id=invocation_id,
                new_model_calls=len(new_keys),
                new_trial_keys=new_keys,
                cached_or_recovered_trials=len(planned) - len(new_keys),
                trials=[dict(start=starts[p["key"]], outcome=ends[p["key"]]) for p in planned],
            )
            all_keys = {p["key"] for p in planned}
            for group, keys in (
                ("new_usage", set(new_keys)),
                ("historical_usage", all_keys - set(new_keys)),
            ):
                result[group] = {}
                for field in ("input_tokens", "output_tokens"):
                    values = [
                        ends[k]["execution"]["generation"][field]
                        if ends[k]["execution"] and ends[k]["execution"]["generation"]
                        else None
                        for k in keys
                    ]
                    result[group][field] = (
                        sum(values) if all(v is not None for v in values) else None
                    )
            result["monetary_cost"] = None
            self.store.append(
                "native_invocation", {k: v for k, v in result.items() if k != "trials"}
            )
            _save(self.store.root / "invocations" / (invocation_id + ".json"), result)
            _save(self.store.root / "exports" / (manifest_id + ".json"), result)
            return result

    @staticmethod
    def _recover(start, raw):
        evidence = DirectionEvidence.model_validate(start["package"]["evidence"])
        generation = Generation.model_validate(raw)
        prediction, failure, error = None, "parse", None
        try:
            if generation.status != "complete":
                failure = "generate"
                raise GenerationFailure(generation)
            prediction = parse_json(generation.text, DirectionPrediction)
            failure = "binding"
            if (
                prediction.case_id != evidence.case_id
                or prediction.package_digest != evidence.package_digest
            ):
                raise ValueError("Prediction case/package binding mismatch")
            failure = None
        except (ValueError, TypeError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        return PredictionExecution(
            run_id=start["attempt_id"],
            prompt_version=prompt_version_for(PromptCondition.model_validate(start["condition"])),
            evidence=evidence,
            package_digest=evidence.package_digest,
            display_sample_digest=evidence.display_sample_digest,
            prompt_condition=PromptCondition.model_validate(start["condition"]),
            prompt_digest=canonical_digest(start["messages"]),
            request_messages=start["messages"],
            output_schema=start["output_schema"],
            generation_config=start["config"],
            generation=generation,
            prediction=prediction,
            failure_stage=failure,
            error=error,
            latency_seconds=generation.latency_seconds,
        )

    @staticmethod
    def _finish(start, trace, *, recovered):
        context = None
        if trace.failure_stage is None:
            context = VerificationContext(
                **start["receipt"], proposal_digest=trace.prediction.proposal_digest
            )
        return dict(
            key=start["key"],
            execution=trace.model_dump(mode="json"),
            context=context.model_dump(mode="json") if context else None,
            operational_error=None,
            recovered=recovered,
            recovered_latency_unknown=recovered,
        )

    def replay_s2(self, manifest_id):
        import json

        with self.store.locked():
            manifest = json.loads(
                (self.store.root / "manifests" / (manifest_id + ".json")).read_text()
            )
            if canonical_digest(manifest["expected_keys"]).removeprefix("sha256:") != manifest_id:
                raise ValueError("Manifest identity mismatch")
            starts, ends, prior = (
                self.store.by_key(k)
                for k in ("native_started", "native_finished", "native_released")
            )
            records = []
            checker_version = PredictionCheck.model_fields["checker_version"].default
            for key in manifest["expected_keys"]:
                start, end = starts[key], ends[key]
                if start["condition"]["condition_id"] != "S1":
                    continue
                cache_key = canonical_digest([key, end, checker_version])
                if cache_key in prior:
                    records.append(prior[cache_key])
                    continue
                record = dict(
                    key=cache_key,
                    source_key=key,
                    source_attempt_id=start["attempt_id"],
                    source_run_id=None,
                    check=None,
                    released_direction=None,
                    skip_reason=None,
                    parent_outcome_digest=canonical_digest(end),
                )
                if end["execution"] is None or end["execution"]["failure_stage"] is not None:
                    record["skip_reason"] = "parent_prediction_failed"
                else:
                    trace = PredictionExecution.model_validate(end["execution"])
                    record["source_run_id"] = trace.run_id
                    try:
                        context = VerificationContext.model_validate(end["context"])
                        checked = check_prediction(
                            trace.evidence, trace.prediction, context=context
                        )
                        record["check"] = checked.model_dump(mode="json")
                        if checked.release:
                            record["released_direction"] = trace.prediction.predicted_direction
                    except (ValueError, TypeError) as exc:
                        record["skip_reason"] = "checker_error"
                        record["error"] = f"{type(exc).__name__}: {exc}"
                self.store.append("native_released", record)
                records.append(record)
            _save(self.store.root / "exports" / (manifest_id + "-s2.json"), records)
            return records

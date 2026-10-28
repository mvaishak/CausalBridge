"""Vaishak's public orchestration entry point and evaluation trace."""

from time import perf_counter
from uuid import uuid4

from pydantic import Field, ValidationError

from causalbridge.llm.client import Generation, JSONModel, ModelConfig
from causalbridge.llm.parser import (
    PROMPT_VERSION,
    interpretation_messages,
    parse_json,
    plan_messages,
    query_messages,
)
from causalbridge.llm.tool_planner import plan_request
from causalbridge.schemas import (
    Proposal,
    Query,
    Record,
    RuntimeCase,
    ToolRequest,
    ToolResult,
    Verdict,
)
from causalbridge.tools.protocol import ToolBackend
from causalbridge.verifier.contracts import abstention, check_operation, check_preconditions, verify


class LLMCall(Record):
    stage: str
    messages: tuple[dict[str, str], ...]
    output_schema: dict
    generation: Generation | None = None
    error: str | None = None


class RunTrace(Record):
    schema_version: str = "1.0"
    prompt_version: str = PROMPT_VERSION
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    runtime_case: RuntimeCase
    query_source: str
    model_mode: str
    generation_config: ModelConfig | None = None
    numeric_tolerance: float
    sign_tolerance: float
    query: Query | None = None
    plan: Proposal | None = None
    final_proposal: Proposal | None = None
    tool_request: ToolRequest | None = None
    tool_result: ToolResult | None = None
    tool_executed: bool = False
    calls: tuple[LLMCall, ...] = ()
    verdict: Verdict
    failure_stage: str | None = None
    latency_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None


class CausalBridge:
    def __init__(
        self,
        model: JSONModel,
        backend: ToolBackend,
        *,
        numeric_tolerance=1e-3,
        sign_tolerance=1e-9,
        model_mode="live",
    ):
        import math

        if any(not math.isfinite(t) or t < 0 for t in (numeric_tolerance, sign_tolerance)):
            raise ValueError("Tolerances must be finite and nonnegative")
        self.model, self.backend = model, backend
        self.numeric_tolerance, self.sign_tolerance = numeric_tolerance, sign_tolerance
        self.model_mode = model_mode

    def run(self, case: RuntimeCase, *, query: Query | None = None) -> RunTrace:
        started = perf_counter()
        # Separate snapshot prevents callers mutating evidence during a run.
        case = RuntimeCase.model_validate_json(case.model_dump_json())
        calls = []
        state = dict(
            runtime_case=case,
            query_source="public_query_spec" if query else "llm_parser",
            query=query,
            model_mode=self.model_mode,
            generation_config=getattr(self.model, "config", None),
            numeric_tolerance=self.numeric_tolerance,
            sign_tolerance=self.sign_tolerance,
        )

        def finish(verdict, failure_stage=None):
            generations = [c.generation for c in calls if c.generation is not None]

            def total(field):
                values = [getattr(g, field) for g in generations]
                return sum(values) if values and all(v is not None for v in values) else None

            return RunTrace(
                **state,
                calls=tuple(calls),
                verdict=verdict,
                failure_stage=failure_stage,
                latency_seconds=perf_counter() - started,
                input_tokens=total("input_tokens"),
                output_tokens=total("output_tokens"),
            )

        def generate(stage, prompt, shape):
            schema = shape.model_json_schema()
            try:
                generation = self.model.generate(prompt, schema)
            except Exception as exc:
                calls.append(
                    LLMCall(
                        stage=stage,
                        messages=tuple(prompt),
                        output_schema=schema,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                raise RuntimeError("model_error") from exc
            calls.append(
                LLMCall(
                    stage=stage, messages=tuple(prompt), output_schema=schema, generation=generation
                )
            )
            return parse_json(generation.text, shape)

        stage = "parse"
        try:
            if query is None:
                query = generate(stage, query_messages(case), Query)
                state["query"] = query
            query.bind(case)
            stage = "plan"
            plan = generate(stage, plan_messages(case, query), Proposal)
            state["plan"] = plan
            request = plan_request(query, plan, case)
            state["tool_request"] = request
            if plan.response_action == "abstain":
                return finish(
                    abstention(
                        "unsupported",
                        "model_abstention",
                        "The model abstained; evidence insufficiency has not been established.",
                    )
                )
            operation_error = check_operation(query, plan, request)
            if operation_error is not None:
                return finish(operation_error)
            missing = check_preconditions(request, case)
            if missing:
                return finish(
                    abstention(
                        "unsupported",
                        "missing_evidence",
                        "The selected operation's evidence requirements are not satisfied.",
                        missing,
                    )
                )
            stage = "execute"
            state["tool_executed"] = True
            try:
                result = ToolResult.model_validate(self.backend.execute(request, case))
            except Exception as exc:
                result = ToolResult(request=request, error=f"{type(exc).__name__}: {exc}")
            state["tool_result"] = result
            if result.error is not None:
                return finish(verify(query, plan, request, result, case), stage)
            stage = "interpret"
            final = generate(stage, interpretation_messages(case, plan, result), Proposal)
            state["final_proposal"] = final
            if (
                final.query != plan.query
                or final.requested_operation != plan.requested_operation
                or final.proposed_tool != plan.proposed_tool
            ):
                return finish(
                    abstention(
                        "execution_error",
                        "final_plan_changed",
                        "The model changed query roles or operations after tool execution.",
                    ),
                    stage,
                )
            return finish(
                verify(
                    query,
                    final,
                    request,
                    result,
                    case,
                    numeric_tolerance=self.numeric_tolerance,
                    sign_tolerance=self.sign_tolerance,
                )
            )
        except RuntimeError as exc:
            return finish(
                abstention(
                    "execution_error",
                    "model_error",
                    "Model generation failed: " + str(exc.__cause__ or exc),
                ),
                stage,
            )
        except (ValueError, ValidationError, TypeError) as exc:
            return finish(
                abstention(
                    "execution_error",
                    "structured_output_error",
                    "Query or structured output validation failed: " + str(exc),
                ),
                stage,
            )

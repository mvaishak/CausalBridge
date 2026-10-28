"""Small visible-only development adapter, replaceable by Anish's engine.

Exact enumeration is capped at 12 nodes. This is not a benchmark generator or
independent ground-truth validator. Never give this adapter withheld CPTs.
"""

from itertools import product
from math import prod

from causalbridge.schemas import Query, RuntimeCase, ToolRequest, ToolResult
from causalbridge.tools.graph import has_path, valid_adjustment


def intervention(case: RuntimeCase, query: Query, treatment: int) -> float:
    if len(case.graph_nodes) > 12:
        raise ValueError("Development enumeration adapter supports at most 12 nodes")
    cpts = {c.node: c for c in case.visible_cpts}
    total = 0.0
    for bits in product((0, 1), repeat=len(case.graph_nodes)):
        assignment = dict(zip(case.graph_nodes, bits, strict=True))
        if assignment[query.cause] != treatment or assignment[query.outcome] != 1:
            continue
        factors = []
        for node in case.graph_nodes:
            if node == query.cause:
                continue  # Truncated factorization: replace X's mechanism by do(X=x).
            cpt = cpts[node]
            key = "".join(str(assignment[p]) for p in cpt.parents)
            p = cpt.p_one[key]
            factors.append(p if assignment[node] else 1 - p)
        total += prod(factors)
    return total


def adjusted_probability(case: RuntimeCase, query: Query) -> float:
    joint = case.visible_joint
    if joint is None:
        raise ValueError("Missing visible joint distribution")
    rows = [
        (dict(zip(joint.variables, map(int, key), strict=True)), p)
        for key, p in joint.probabilities.items()
    ]
    total = 0.0
    for bits in product((0, 1), repeat=len(query.adjustment_set)):
        z = dict(zip(query.adjustment_set, bits, strict=True))
        matching = [(a, p) for a, p in rows if all(a[n] == v for n, v in z.items())]
        pz = sum(p for _, p in matching)
        pxz = sum(p for a, p in matching if a[query.cause] == query.intervention_value)
        pyxz = sum(
            p
            for a, p in matching
            if a[query.cause] == query.intervention_value and a[query.outcome] == 1
        )
        if pxz <= 0:
            raise ValueError("Adjustment violates positivity")
        total += pyxz / pxz * pz
    return total


class ReferenceBackend:
    def execute(self, request: ToolRequest, case: RuntimeCase) -> ToolResult:
        from causalbridge.verifier.contracts import check_preconditions

        try:
            if request.evidence_digest != case.evidence_digest():
                raise ValueError("Evidence digest mismatch")
            request.query.bind(case)
            missing = check_preconditions(request, case)
            if missing:
                raise ValueError("Missing preconditions: " + ", ".join(missing))
            q = request.query
            match request.operation:
                case "has_directed_path":
                    value = has_path(case, q)
                case "is_valid_adjustment_set":
                    value = valid_adjustment(case, q)
                case "compute_effect":
                    value = (
                        intervention(case, q, q.to_value) - intervention(case, q, q.from_value)
                        if has_path(case, q)
                        else 0.0
                    )
                case "compute_intervention":
                    value = intervention(case, q, q.intervention_value)
                case "backdoor_adjustment":
                    value = adjusted_probability(case, q)
                case _:
                    raise ValueError("Unsupported operation")
            return ToolResult(request=request, value=value)
        except (ValueError, KeyError, ArithmeticError) as exc:
            return ToolResult(request=request, error=str(exc))

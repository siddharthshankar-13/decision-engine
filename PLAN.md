# Decision Engine Roadmap

## Phase 1 - Graph model foundation (complete)

Generic typed `Graph`, `Node`, `Field`, `Dependency`, and `Constraint`
dataclasses represent systems. Relationships, transformations, and rules are
stored for inspection only; nothing is executed in Phase 1.

The pricing example is built by `build_pricing_graph()`. The existing
hardcoded `pricing_model()` remains in `simulation.py` for comparison.

## Phase 1 status

Phase 1 is complete after automated verification of ownership, duplicate-name
rejection, structural dependencies, constraints, and non-execution behavior.

## Phase 2 - Monte Carlo simulation and domain model (complete)

- Add typed `Decision`, `Assumption`, `SimulationRun`, and `SimulationResult` objects.
- Support distribution-based uncertainty, reproducible seeds, and P10/P50/P90 outcomes.
## Phase 3 - Field lookup and dependency propagation (complete)

- Resolve canonical `node.field` references.
- Execute callable dependency transformations and propagate values.
- Preserve opaque, non-callable transformations as structural only.
- Detect missing values and dependency cycles.

## Phase 4 - Constraint evaluation and decision support (active)

- Evaluate callable constraint rules against graph field values.
- Return structured constraint violations for failed rules.
- Keep opaque, non-callable rules structural only.

## Phase 5 - Scenarios and uncertainty analysis (complete)

- Implemented `Scenario` assumption/distribution overrides and `compare_scenarios()`.
- Comparisons retain per-scenario runs, P10/P50/P90, and differences in P50
  against an explicitly named baseline. Baseline means reference assumptions;
  it does not automatically remove a decision's effect.
- Tested baseline, optimistic, expected, and stress pricing scenarios with
  10,000 trials, seeds, input preservation, and invalid overrides.
- Current simulation compatibility: `Decision` is recorded as metadata;
  model inputs such as `price_increase` must be supplied as assumptions.
- Implemented correlation-based sensitivity analysis that ranks assumptions
  for a selected outcome and preserves correlation direction.

## Next task

- Phase 6: define structured AI critique inputs and outputs, then add finance,
  sales, and operations critic interfaces.

Run the current suite with:

```text
python -m pytest -q -p no:cacheprovider test_graph.py test_simulation.py test_scenarios.py test_sensitivity.py
```

Engine and future FastAPI backend use Python; the future dashboard uses
TypeScript/Next.js. Monte Carlo remains the only simulation method in scope.

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

## Phase 4 - Constraint evaluation and decision support (complete)

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

## Phase 6 - Structured AI critique (complete)

- Added validated critique context, evidence, severity, confidence, and output
  contracts.
- Added statically distinct finance, sales, and operations critic interfaces.
- Added a compact JSON provider payload that excludes raw trial outcomes.
- Added provider-independent callable adapters and strict response parsing.
- Added critique aggregation with one critic per domain, domain ownership
  checks, and strongest-objection selection.
- No external LLM is called by the domain layer. A concrete SDK integration can
  be selected later without changing these contracts.

## Phase 7 - Unified decision report (complete)

- Combine a decision, assumptions, simulation results, scenario comparison,
  sensitivity results, affected fields, impact paths, critiques, and key risks.
- Calculate expected outcomes and positive/negative outcome probabilities.
- Keep report construction separate from simulation execution.

## Phase 8 - Company policy and multidisciplinary AI red-team (pending)

This is a first-class MVP capability. Generic graph constraints and the current
finance, sales, and operations critic contracts are foundations, but they do
not yet constitute policy understanding or a complete red-team process.

### Company policy framework

- Define typed `Policy`, `PolicyVersion`, `PolicyScope`, `PolicyRule`,
  `PolicyException`, and `PolicyEvaluation` objects.
- Record policy owner, source/provenance, status, effective dates, version, and
  affected decisions, fields, departments, products, or risk categories.
- Distinguish mandatory controls, approval requirements, risk thresholds, and
  advisory guidance.
- Determine which policy versions apply to a decision and evaluate their rules
  against decision, graph, simulation, scenario, and report data.
- Support documented exceptions/waivers with owner, reason, approval, and
  expiration rather than silently bypassing a rule.
- Detect conflicting policies and return an explainable evaluation trace that
  links every result to its policy version and evidence.
- Keep natural-language policy extraction separate from authoritative policy
  objects; AI-proposed interpretations require human review before activation.
- Add policy evaluations, violations, required approvals, and exceptions to
  the unified decision report.

### Multidisciplinary AI red-team

- Generalize critic configuration beyond finance, sales, and operations to
  perspectives such as legal, compliance, security, privacy, HR/people,
  customer, ethics, and strategy.
- Run first-round reviews independently so one critic does not anchor the
  others, then support explicit challenges/rebuttals and a final synthesis.
- Require each objection to cite simulation evidence, policy evidence, or an
  explicitly labeled qualitative concern.
- Preserve material disagreement and minority objections instead of forcing a
  false consensus.
- Track critic role, provider/model, prompt version, confidence, severity,
  evidence, timestamps, and failures for auditability and reproducibility.
- Add safeguards for prompt injection, untrusted policy text, sensitive data,
  timeouts, malformed responses, and partial provider failure.
- Keep AI advisory: critics cannot alter simulations, activate policies,
  approve exceptions, or make the final decision.

### Phase 8 acceptance criteria

- A decision can be evaluated against every applicable, versioned policy and
  produce traceable pass, fail, approval-required, or not-applicable results.
- A configurable set of multidisciplinary critics can independently review the
  same decision and return validated evidence-backed objections.
- The engine can aggregate and synthesize reviews while retaining dissent and
  clearly separating quantitative facts, policy findings, and AI judgment.
- Tests cover policy applicability, versions, conflicts, exceptions, critic
  independence, malformed/failed critics, rebuttals, synthesis, and audit data.

## Phase 9 - Backend API (pending)

- Add a FastAPI application and validated decision, simulation, and report
  endpoints after the Python report contract is stable.
- Add persistence only after the API resource model is reviewed.

## Phase 10 - MVP dashboard (pending)

- Add a TypeScript/Next.js interface for decision entry, assumptions, outcome
  charts, scenarios, sensitivity, graph impacts, critiques, and reports.
- Keep decision math and simulation execution in Python.

## Phase 11 - Demo decision (pending)

- Model the fictional Acme SaaS pricing decision with realistic assumptions.
- Demonstrate the complete assumption-to-simulation-to-impact-to-critique flow.

## Roadmap status

Phases 1-7 are complete. Phase 8 is next; Phases 9-11 follow in order.

Run the current suite with:

```text
python -m pytest -q
```

Engine and future FastAPI backend use Python; the future dashboard uses
TypeScript/Next.js. Monte Carlo remains the only simulation method in scope.

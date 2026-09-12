"""Named assumption scenarios for the existing Monte Carlo engine."""

from dataclasses import dataclass
from typing import Callable, Mapping, Any, Sequence

from simulation import Assumption, Decision, SimulationRun, run_simulation


@dataclass(frozen=True)
class Scenario:
    name: str
    overrides: tuple[Assumption, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Scenario name must be a non-empty string")
        overrides = tuple(self.overrides)
        if any(not isinstance(item, Assumption) for item in overrides):
            raise TypeError("Scenario overrides must be Assumption objects")
        if len({item.name for item in overrides}) != len(overrides):
            raise ValueError("Scenario override names must be unique")
        object.__setattr__(self, "overrides", overrides)


@dataclass
class ScenarioComparison:
    baseline: str
    runs: dict[str, SimulationRun]
    p50_deltas: dict[str, dict[str, float]]


def compare_scenarios(
    decision: Decision,
    assumptions: Sequence[Assumption],
    model: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    scenarios: Sequence[Scenario],
    baseline: str,
    trials: int = 10_000,
    seed: int | None = None,
) -> ScenarioComparison:
    """Compare percentile summaries against an explicitly named reference scenario.

    Overrides replace whole assumptions, including their distributions. Unknown
    names are rejected before running models. Input assumptions are not changed.
    Each scenario reuses the supplied seed and assumption order; this is not a
    guarantee of paired samples when overrides change which fields are sampled.
    Deltas are differences of medians, not medians of per-trial differences.
    The baseline is a reference scenario, not an automatic no-decision run.
    """
    base = tuple(assumptions)
    scenarios = tuple(scenarios)
    if any(not isinstance(item, Assumption) for item in base):
        raise TypeError("assumptions must contain Assumption objects")
    names = {item.name for item in base}
    if len(names) != len(base):
        raise ValueError("Assumption names must be unique")
    if any(not isinstance(item, Scenario) for item in scenarios):
        raise TypeError("scenarios must contain Scenario objects")
    scenario_names = {item.name for item in scenarios}
    if len(scenario_names) != len(scenarios):
        raise ValueError("Scenario names must be unique")
    if baseline not in scenario_names:
        raise ValueError("baseline must name one of the supplied scenarios")
    for scenario in scenarios:
        unknown = {item.name for item in scenario.overrides} - names
        if unknown:
            raise ValueError(f"Unknown assumptions in {scenario.name!r}: {sorted(unknown)}")

    runs = {}
    for scenario in scenarios:
        overrides = {item.name: item for item in scenario.overrides}
        effective = tuple(overrides.get(item.name, item) for item in base)
        runs[scenario.name] = run_simulation(decision, effective, model, trials, seed)
    reference = runs[baseline].result.p50
    if any(set(run.result.p50) != set(reference) for run in runs.values()):
        raise ValueError("Model output keys must match across scenarios")
    deltas = {
        name: {key: run.result.p50[key] - reference[key] for key in reference}
        for name, run in runs.items()
    }
    return ScenarioComparison(baseline, runs, deltas)

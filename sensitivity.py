"""Correlation-based sensitivity analysis for Monte Carlo runs."""

from dataclasses import dataclass

import numpy as np

from simulation import SimulationRun


@dataclass(frozen=True)
class SensitivityScore:
    assumption: str
    correlation: float

    @property
    def magnitude(self) -> float:
        return abs(self.correlation)


@dataclass(frozen=True)
class SensitivityResult:
    outcome: str
    scores: tuple[SensitivityScore, ...]


def analyze_sensitivity(run: SimulationRun, outcome: str) -> SensitivityResult:
    """Rank numeric assumptions by Pearson correlation with an outcome."""
    if outcome not in run.result.p50:
        raise KeyError(f"Unknown simulation outcome: {outcome!r}")
    if not run.result.sampled_assumptions:
        raise ValueError("Simulation run does not contain sampled assumptions")

    outcome_values = np.asarray(
        [trial[outcome] for trial in run.result.outcomes], dtype=float
    )
    scores = []
    for assumption in run.assumptions:
        try:
            values = np.asarray(
                [sample[assumption.name] for sample in run.result.sampled_assumptions],
                dtype=float,
            )
        except (TypeError, ValueError):
            continue
        if np.std(values) == 0 or np.std(outcome_values) == 0:
            correlation = 0.0
        else:
            correlation = float(np.corrcoef(values, outcome_values)[0, 1])
        scores.append(SensitivityScore(assumption.name, correlation))

    scores.sort(key=lambda score: (-score.magnitude, score.assumption))
    return SensitivityResult(outcome, tuple(scores))

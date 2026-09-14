"""Unified decision report for simulation and decision-support outputs."""

from dataclasses import dataclass, field
from math import isfinite
from statistics import fmean
from types import MappingProxyType
from typing import Mapping, Sequence

from critique_aggregation import CritiqueCollection
from scenarios import ScenarioComparison
from sensitivity import SensitivityResult
from simulation import Assumption, Decision, SimulationResult, SimulationRun


@dataclass(frozen=True)
class OutcomeSummary:
    metric: str
    expected: float
    p10: float
    p50: float
    p90: float
    probability_positive: float
    probability_negative: float

    def __post_init__(self) -> None:
        if not isinstance(self.metric, str) or not self.metric.strip():
            raise ValueError("Outcome metric must be a non-empty string")
        values = (self.expected, self.p10, self.p50, self.p90)
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not isfinite(value)
            for value in values
        ):
            raise ValueError("Outcome statistics must be finite numbers")
        probabilities = (self.probability_positive, self.probability_negative)
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not 0 <= value <= 1
            for value in probabilities
        ):
            raise ValueError("Outcome probabilities must be between 0 and 1")
        if self.probability_positive + self.probability_negative > 1 + 1e-12:
            raise ValueError("Positive and negative probabilities cannot exceed 1")
        for name in (
            "expected",
            "p10",
            "p50",
            "p90",
            "probability_positive",
            "probability_negative",
        ):
            object.__setattr__(self, name, float(getattr(self, name)))


@dataclass(frozen=True)
class ImpactPath:
    """An inspectable upstream-to-downstream chain of canonical field names."""

    fields: tuple[str, ...]

    def __post_init__(self) -> None:
        fields = tuple(self.fields)
        if len(fields) < 2:
            raise ValueError("An impact path requires at least two fields")
        if any(not isinstance(item, str) or not item.strip() for item in fields):
            raise ValueError("Impact paths require non-empty field references")
        object.__setattr__(self, "fields", fields)


@dataclass(frozen=True)
class DecisionReport:
    run: SimulationRun
    outcomes: Mapping[str, OutcomeSummary]
    scenario_comparison: ScenarioComparison | None = None
    sensitivities: tuple[SensitivityResult, ...] = ()
    affected_fields: tuple[str, ...] = ()
    impact_paths: tuple[ImpactPath, ...] = ()
    critiques: CritiqueCollection = field(default_factory=lambda: CritiqueCollection(()))
    key_risks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.run, SimulationRun):
            raise TypeError("run must be a SimulationRun")

        outcomes = dict(self.outcomes)
        if not outcomes:
            raise ValueError("A decision report requires outcome summaries")
        if any(
            not isinstance(summary, OutcomeSummary) or key != summary.metric
            for key, summary in outcomes.items()
        ):
            raise ValueError("Outcome keys must match their OutcomeSummary metrics")
        if set(outcomes) != set(self.run.result.p50):
            raise ValueError("Outcome summaries must match simulation result metrics")

        if self.scenario_comparison is not None:
            if not isinstance(self.scenario_comparison, ScenarioComparison):
                raise TypeError("scenario_comparison must be a ScenarioComparison")
            if any(
                scenario_run.decision != self.run.decision
                for scenario_run in self.scenario_comparison.runs.values()
            ):
                raise ValueError("Scenario runs must use the report decision")
            if any(
                set(scenario_run.result.p50) != set(outcomes)
                for scenario_run in self.scenario_comparison.runs.values()
            ):
                raise ValueError("Scenario metrics must match report outcomes")

        sensitivities = tuple(self.sensitivities)
        if any(not isinstance(item, SensitivityResult) for item in sensitivities):
            raise TypeError("sensitivities must contain SensitivityResult objects")
        sensitivity_outcomes = [item.outcome for item in sensitivities]
        if len(set(sensitivity_outcomes)) != len(sensitivity_outcomes):
            raise ValueError("Only one sensitivity result is allowed per outcome")
        if set(sensitivity_outcomes) - set(outcomes):
            raise ValueError("Sensitivity results must reference report outcomes")

        affected_fields = tuple(self.affected_fields)
        if any(not isinstance(item, str) or not item.strip() for item in affected_fields):
            raise ValueError("affected_fields must contain non-empty field references")
        if len(set(affected_fields)) != len(affected_fields):
            raise ValueError("affected_fields must be unique")

        impact_paths = tuple(self.impact_paths)
        if any(not isinstance(item, ImpactPath) for item in impact_paths):
            raise TypeError("impact_paths must contain ImpactPath objects")

        if not isinstance(self.critiques, CritiqueCollection):
            raise TypeError("critiques must be a CritiqueCollection")

        key_risks = tuple(self.key_risks)
        if any(not isinstance(item, str) or not item.strip() for item in key_risks):
            raise ValueError("key_risks must contain non-empty strings")
        if len(set(key_risks)) != len(key_risks):
            raise ValueError("key_risks must be unique")

        object.__setattr__(self, "outcomes", MappingProxyType(outcomes))
        object.__setattr__(self, "sensitivities", sensitivities)
        object.__setattr__(self, "affected_fields", affected_fields)
        object.__setattr__(self, "impact_paths", impact_paths)
        object.__setattr__(self, "key_risks", key_risks)

    @property
    def decision(self) -> Decision:
        return self.run.decision

    @property
    def assumptions(self) -> tuple[Assumption, ...]:
        return self.run.assumptions

    @property
    def simulation_result(self) -> SimulationResult:
        return self.run.result


def build_decision_report(
    run: SimulationRun,
    *,
    scenario_comparison: ScenarioComparison | None = None,
    sensitivities: Sequence[SensitivityResult] = (),
    affected_fields: Sequence[str] = (),
    impact_paths: Sequence[ImpactPath] = (),
    critiques: CritiqueCollection | None = None,
    key_risks: Sequence[str] = (),
) -> DecisionReport:
    """Combine existing engine outputs without rerunning the simulation."""
    if not isinstance(run, SimulationRun):
        raise TypeError("run must be a SimulationRun")
    result = run.result
    if not result.outcomes:
        raise ValueError("Simulation result must contain trial outcomes")
    if len(result.outcomes) != result.trials:
        raise ValueError("Simulation trial count must match stored outcomes")
    metric_keys = set(result.p50)
    if set(result.p10) != metric_keys or set(result.p90) != metric_keys:
        raise ValueError("Simulation percentile metrics must match")
    if any(set(outcome) != metric_keys for outcome in result.outcomes):
        raise ValueError("Every trial must contain the simulation result metrics")

    summaries = {}
    for metric in result.p50:
        try:
            values = [float(outcome[metric]) for outcome in result.outcomes]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Outcome {metric!r} must be numeric in every trial") from error
        count = len(values)
        summaries[metric] = OutcomeSummary(
            metric=metric,
            expected=fmean(values),
            p10=result.p10[metric],
            p50=result.p50[metric],
            p90=result.p90[metric],
            probability_positive=sum(value > 0 for value in values) / count,
            probability_negative=sum(value < 0 for value in values) / count,
        )

    return DecisionReport(
        run=run,
        outcomes=summaries,
        scenario_comparison=scenario_comparison,
        sensitivities=tuple(sensitivities),
        affected_fields=tuple(affected_fields),
        impact_paths=tuple(impact_paths),
        critiques=critiques or CritiqueCollection(()),
        key_risks=tuple(key_risks),
    )

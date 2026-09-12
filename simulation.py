"""Monte Carlo simulation primitives for the decision engine MVP."""

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import numpy as np

price = 100

customers = 10000

elasticity_mean = -1.2

elasticity_std = 0.1

price_increase = 0.1

trials = 10000

# ***

# Monte Carlo Simulation Function
# params: assumptions, trials
# eventually we want this to be generlizable to all decisions
# One of three Simulation Methods we'll use:
# Monte Carlo simulation, discrete-event simulation, and agent-based modeling
# Finite Element Methods, System Dynamics
# ***

@dataclass(frozen=True)
class NormalDistribution:
    mean: float
    std: float

    def __post_init__(self) -> None:
        if self.std < 0:
            raise ValueError("Normal distribution std must be non-negative")

    def sample(self, rng: np.random.Generator) -> float:
        return float(rng.normal(self.mean, self.std))


@dataclass(frozen=True)
class Assumption:
    name: str
    value: Any = None
    distribution: NormalDistribution | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Assumption name must be a non-empty string")
        if self.distribution is not None and self.value is not None:
            raise ValueError("An assumption cannot have both value and distribution")
        if self.distribution is None and self.value is None:
            raise ValueError("An assumption requires a value or distribution")

    def sample(self, rng: np.random.Generator) -> Any:
        return self.distribution.sample(rng) if self.distribution else self.value


@dataclass(frozen=True)
class Decision:
    name: str
    description: str = ""
    changes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Decision name must be a non-empty string")


@dataclass
class SimulationResult:
    outcomes: list[Mapping[str, Any]]
    p10: dict[str, float]
    p50: dict[str, float]
    p90: dict[str, float]
    trials: int
    seed: int | None = None
    sampled_assumptions: list[Mapping[str, Any]] = field(default_factory=list)


@dataclass
class SimulationRun:
    decision: Decision
    assumptions: tuple[Assumption, ...]
    result: SimulationResult


def _simulate_trials(model, assumptions, trials: int, seed: int | None):
    if not isinstance(trials, int) or trials <= 0:
        raise ValueError("trials must be a positive integer")
    rng = np.random.default_rng(seed)
    results = []
    samples = []
    for _ in range(trials):
        sampled_assumptions = {}
        for name, assumption in assumptions.items():
            if isinstance(assumption, Assumption):
                sampled_assumptions[name] = assumption.sample(rng)
            elif isinstance(assumption, dict):
                if set(assumption) != {"mean", "std"}:
                    raise ValueError(
                        "Distribution dictionaries require exactly 'mean' and 'std'"
                    )
                if assumption["std"] < 0:
                    raise ValueError("Normal distribution std must be non-negative")
                sampled_assumptions[name] = float(rng.normal(assumption["mean"], assumption["std"]))
            else:
                sampled_assumptions[name] = assumption
        outcome = model(sampled_assumptions)
        results.append(outcome)
        samples.append(sampled_assumptions)
    return results, samples


def simulate(model: Callable[[Mapping[str, Any]], Mapping[str, Any]], assumptions, trials: int, seed: int | None = None):
    """Run seeded Monte Carlo trials, preserving the original list result API."""
    results, _ = _simulate_trials(model, assumptions, trials, seed)

    return results


def run_simulation(decision: Decision, assumptions: list[Assumption] | tuple[Assumption, ...], model: Callable, trials: int = 10_000, seed: int | None = None) -> SimulationRun:
    """Run a typed simulation and calculate P10/P50/P90 for numeric outputs."""
    if not isinstance(decision, Decision):
        raise TypeError("decision must be a Decision")
    typed_assumptions = tuple(assumptions)
    if len({item.name for item in typed_assumptions}) != len(typed_assumptions):
        raise ValueError("Assumption names must be unique")
    outcomes, samples = _simulate_trials(
        model, {item.name: item for item in typed_assumptions}, trials, seed
    )
    keys = set(outcomes[0])
    if any(set(outcome) != keys for outcome in outcomes):
        raise ValueError("Model must return the same output keys for every trial")
    numeric = {key: np.asarray([outcome[key] for outcome in outcomes], dtype=float) for key in keys}
    result = SimulationResult(outcomes, {k: float(np.percentile(v, 10)) for k, v in numeric.items()},
                              {k: float(np.percentile(v, 50)) for k, v in numeric.items()},
                              {k: float(np.percentile(v, 90)) for k, v in numeric.items()},
                              trials, seed, samples)
    return SimulationRun(decision, typed_assumptions, result)


# ***
# * Sample Simulation Function
# * params : assumptions
# ***

def pricing_model(assumptions):

    price = assumptions["price"]

    customers = assumptions["customers"]

    elasticity = assumptions["elasticity"]

    churn = assumptions["churn"]

    price_increase = assumptions["price_increase"]

    variable_cost = assumptions["variable_cost"]

    new_price = price * (1 + price_increase)

    demand_change = elasticity * price_increase

    new_customers = customers * (1 + demand_change) * (1 - churn)

    new_revenue = new_price * new_customers

    new_cost = variable_cost * new_customers

    new_profit = new_revenue - new_cost

    return {
        "profit": new_profit,
        "cost": new_cost,
        "revenue": new_revenue
    }


assumptions = {
    "price": 100,
    "customers": 10000,
    "elasticity": {
        "mean": -1.2,
        "std": 0.25
    },
    "churn": {
        "mean": 0.04,
        "std": 0.01
    },
    "price_increase": 0.10,
    "variable_cost": 40
}


if __name__ == "__main__":
    results = simulate(pricing_model, assumptions, 10_000, seed=42)


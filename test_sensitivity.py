import pytest

from sensitivity import analyze_sensitivity
from simulation import Assumption, Decision, NormalDistribution, run_simulation


def test_sensitivity_ranks_strongest_assumption_and_direction():
    assumptions = [
        Assumption("strong", distribution=NormalDistribution(0, 1)),
        Assumption("weak", distribution=NormalDistribution(0, 1)),
        Assumption("fixed", 10),
    ]
    run = run_simulation(
        Decision("test"), assumptions,
        lambda values: {"profit": 5 * values["strong"] - .1 * values["weak"]},
        trials=5000, seed=42,
    )
    result = analyze_sensitivity(run, "profit")
    assert result.scores[0].assumption == "strong"
    assert result.scores[0].correlation > .99
    assert next(score for score in result.scores if score.assumption == "weak").correlation < 0
    assert next(score for score in result.scores if score.assumption == "fixed").correlation == 0


def test_sensitivity_is_reproducible():
    assumptions = [Assumption("x", distribution=NormalDistribution(0, 1))]
    model = lambda values: {"result": values["x"]}
    first = run_simulation(Decision("test"), assumptions, model, 100, seed=7)
    second = run_simulation(Decision("test"), assumptions, model, 100, seed=7)
    assert analyze_sensitivity(first, "result") == analyze_sensitivity(second, "result")


def test_unknown_outcome_is_rejected():
    run = run_simulation(
        Decision("test"), [Assumption("x", 1)],
        lambda values: {"result": values["x"]}, trials=1,
    )
    with pytest.raises(KeyError):
        analyze_sensitivity(run, "missing")

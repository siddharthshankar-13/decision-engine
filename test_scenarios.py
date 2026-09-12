from unittest.mock import Mock

import pytest

from scenarios import Scenario, compare_scenarios
from simulation import Assumption, Decision, NormalDistribution, pricing_model


def test_comparison_overrides_and_exact_deltas():
    assumptions = [Assumption("x", 10)]
    scenarios = [Scenario("baseline"), Scenario("stress", (Assumption("x", 3),))]
    result = compare_scenarios(Decision("test"), assumptions,
                               lambda values: {"profit": values["x"] * 2},
                               scenarios, "baseline", trials=10, seed=42)
    assert result.p50_deltas == {"baseline": {"profit": 0}, "stress": {"profit": -14}}
    assert result.runs["stress"].result.p10 == {"profit": 6}
    assert assumptions[0].value == 10
    assert result.runs["baseline"].assumptions[0].value == 10


def test_pricing_10000_trials_reproducible_and_order_independent():
    assumptions = [Assumption("price", 100), Assumption("customers", 10000),
                   Assumption("price_increase", .1), Assumption("variable_cost", 25),
                   Assumption("elasticity", distribution=NormalDistribution(-1.2, .1)),
                   Assumption("churn", .04)]
    scenarios = [Scenario("baseline"),
                 Scenario("optimistic", (Assumption("churn", .01),)),
                 Scenario("expected"),
                 Scenario("stress", (Assumption("elasticity", distribution=NormalDistribution(-2, .1)),))]
    first = compare_scenarios(Decision("price increase"), assumptions, pricing_model,
                              scenarios, "baseline", seed=42)
    second = compare_scenarios(Decision("price increase"), assumptions, pricing_model,
                               scenarios[::-1], "baseline", seed=42)
    assert first.runs == second.runs
    assert first.runs["baseline"].result.trials == 10000
    assert first.p50_deltas["optimistic"]["profit"] > 0
    assert first.p50_deltas["stress"]["profit"] < 0
    assert first.p50_deltas["expected"]["profit"] == 0


@pytest.mark.parametrize("scenarios,baseline", [
    ([], "baseline"),
    ([Scenario("a"), Scenario("a")], "a"),
    ([Scenario("a")], "missing"),
    ([Scenario("a"), Scenario("bad", (Assumption("typo", 1),))], "a"),
])
def test_invalid_comparisons_fail_before_model_execution(scenarios, baseline):
    model = Mock()
    with pytest.raises(ValueError):
        compare_scenarios(Decision("test"), [Assumption("x", 1)], model, scenarios, baseline)
    model.assert_not_called()


def test_scenario_validation():
    with pytest.raises(ValueError):
        Scenario(" ")
    with pytest.raises(ValueError):
        Scenario("duplicate", (Assumption("x", 1), Assumption("x", 2)))
    with pytest.raises(TypeError):
        Scenario("invalid", (1,))


def test_different_output_keys_rejected():
    with pytest.raises(ValueError, match="across scenarios"):
        compare_scenarios(Decision("test"), [Assumption("x", 1)],
                          lambda values: {str(values["x"]): 1},
                          [Scenario("base"), Scenario("other", (Assumption("x", 2),))],
                          "base", trials=1)

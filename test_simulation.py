import pytest

from simulation import Assumption, Decision, NormalDistribution, pricing_model, run_simulation, simulate


def test_seeded_simulation_is_reproducible():
    assumptions = {"x": {"mean": 10, "std": 1}}
    assert simulate(lambda values: {"result": values["x"]}, assumptions, 100, seed=7) == simulate(lambda values: {"result": values["x"]}, assumptions, 100, seed=7)


def test_legacy_distribution_validation():
    model = lambda values: {"result": values["x"]}
    with pytest.raises(ValueError):
        simulate(model, {"x": {"mean": 1}}, 1)
    with pytest.raises(ValueError):
        simulate(model, {"x": {"mean": 1, "std": -1}}, 1)


def test_typed_run_calculates_percentiles():
    run = run_simulation(Decision("test"), [Assumption("x", distribution=NormalDistribution(10, 0))], lambda values: {"result": values["x"]}, trials=10, seed=1)
    assert run.result.trials == 10
    assert run.result.p10["result"] == 10
    assert run.result.p50["result"] == 10
    assert run.result.p90["result"] == 10


def test_pricing_model_runs_through_typed_api():
    assumptions = [Assumption("price", 100), Assumption("customers", 10_000), Assumption("elasticity", distribution=NormalDistribution(-1.2, .1)), Assumption("churn", distribution=NormalDistribution(.04, .01)), Assumption("price_increase", .1), Assumption("variable_cost", 40)]
    run = run_simulation(Decision("raise price"), assumptions, pricing_model, trials=100, seed=42)
    assert set(run.result.p50) == {"profit", "cost", "revenue"}


@pytest.mark.parametrize("factory", [lambda: Decision(""), lambda: Assumption(""), lambda: Assumption("x"), lambda: NormalDistribution(0, -1)])
def test_domain_validation(factory):
    with pytest.raises(ValueError): factory()

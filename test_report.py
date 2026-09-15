import pytest

from critique import (
    CriticDomain,
    Critique,
    CritiqueEvidence,
    CritiqueSeverity,
)
from critique_aggregation import CritiqueCollection
from report import DecisionReport, ImpactPath, OutcomeSummary, build_decision_report
from scenarios import Scenario, compare_scenarios
from sensitivity import analyze_sensitivity
from simulation import (
    Assumption,
    Decision,
    NormalDistribution,
    SimulationResult,
    SimulationRun,
    run_simulation,
)


def fixed_run() -> SimulationRun:
    result = SimulationResult(
        outcomes=[{"profit": -2}, {"profit": 0}, {"profit": 4}],
        p10={"profit": -1.6},
        p50={"profit": 0},
        p90={"profit": 3.2},
        trials=3,
        seed=5,
    )
    return SimulationRun(Decision("Test decision"), (Assumption("x", 1),), result)


def test_report_calculates_expected_value_and_probabilities():
    report = build_decision_report(fixed_run())
    profit = report.outcomes["profit"]
    assert profit.expected == pytest.approx(2 / 3)
    assert profit.p10 == -1.6
    assert profit.probability_positive == pytest.approx(1 / 3)
    assert profit.probability_negative == pytest.approx(1 / 3)
    assert report.decision.name == "Test decision"
    assert report.simulation_result.trials == 3


def test_report_combines_all_existing_decision_support_outputs():
    decision = Decision("Raise price")
    assumptions = [Assumption("x", distribution=NormalDistribution(2, 0.2))]
    model = lambda values: {"profit": values["x"] * 10}
    run = run_simulation(decision, assumptions, model, trials=100, seed=42)
    scenarios = compare_scenarios(
        decision,
        assumptions,
        model,
        [Scenario("baseline"), Scenario("stress", (Assumption("x", 1),))],
        "baseline",
        trials=100,
        seed=42,
    )
    sensitivity = analyze_sensitivity(run, "profit")
    critiques = CritiqueCollection(
        (
            Critique(
                CriticDomain.FINANCE,
                "Downside remains material.",
                (CritiqueEvidence("profit", "p10", run.result.p10["profit"]),),
                CritiqueSeverity.MEDIUM,
                0.8,
                "x",
            ),
        )
    )
    path = ImpactPath(("product.price", "financials.revenue", "financials.profit"))

    report = build_decision_report(
        run,
        scenario_comparison=scenarios,
        sensitivities=[sensitivity],
        affected_fields=["product.price", "financials.profit"],
        impact_paths=[path],
        critiques=critiques,
        key_risks=["Demand may fall faster than modeled."],
    )

    assert report.scenario_comparison is scenarios
    assert report.sensitivities == (sensitivity,)
    assert report.impact_paths == (path,)
    assert report.critiques.strongest.domain is CriticDomain.FINANCE
    assert report.key_risks == ("Demand may fall faster than modeled.",)


def test_report_outcomes_are_read_only():
    report = build_decision_report(fixed_run())
    with pytest.raises(TypeError):
        report.outcomes["other"] = report.outcomes["profit"]


def test_impact_path_requires_a_chain():
    with pytest.raises(ValueError, match="at least two"):
        ImpactPath(("product.price",))


def test_report_rejects_sensitivity_for_unknown_outcome():
    run = run_simulation(
        Decision("Test"),
        [Assumption("x", distribution=NormalDistribution(1, 0.1))],
        lambda values: {"profit": values["x"]},
        trials=10,
        seed=1,
    )
    sensitivity = analyze_sensitivity(
        run_simulation(
            Decision("Other"),
            [Assumption("x", distribution=NormalDistribution(1, 0.1))],
            lambda values: {"revenue": values["x"]},
            trials=10,
            seed=1,
        ),
        "revenue",
    )
    with pytest.raises(ValueError, match="report outcomes"):
        build_decision_report(run, sensitivities=[sensitivity])


def test_report_rejects_scenarios_for_another_decision():
    run = fixed_run()
    comparison = compare_scenarios(
        Decision("Another decision"),
        [Assumption("x", 1)],
        lambda values: {"profit": values["x"]},
        [Scenario("baseline")],
        "baseline",
        trials=1,
    )
    with pytest.raises(ValueError, match="report decision"):
        build_decision_report(run, scenario_comparison=comparison)


def test_outcome_summary_rejects_impossible_probabilities():
    with pytest.raises(ValueError, match="cannot exceed"):
        OutcomeSummary("profit", 1, 1, 1, 1, 0.8, 0.4)


def test_report_requires_trial_outcomes():
    run = fixed_run()
    run.result.outcomes = []
    with pytest.raises(ValueError, match="trial outcomes"):
        build_decision_report(run)


def test_report_rejects_mismatched_trial_count():
    run = fixed_run()
    run.result.trials = 4
    with pytest.raises(ValueError, match="trial count"):
        build_decision_report(run)


def test_report_rejects_mismatched_percentile_metrics():
    run = fixed_run()
    run.result.p90 = {"revenue": 3.2}
    with pytest.raises(ValueError, match="percentile metrics"):
        build_decision_report(run)


def test_report_rejects_non_summary_outcome_values():
    run = fixed_run()
    with pytest.raises(ValueError, match="Outcome keys"):
        DecisionReport(run, {"profit": "not a summary"})


@pytest.mark.parametrize(
    "args, message",
    [
        (("", 1, 1, 1, 1, 0.5, 0.5), "metric"),
        (("profit", float("inf"), 1, 1, 1, 0.5, 0.5), "finite"),
        (("profit", 1, 1, 1, 1, -0.1, 0.5), "between 0 and 1"),
    ],
)
def test_outcome_summary_validates_fields(args, message):
    with pytest.raises(ValueError, match=message):
        OutcomeSummary(*args)


def test_impact_path_rejects_blank_fields():
    with pytest.raises(ValueError, match="non-empty"):
        ImpactPath(("product.price", " "))


def test_report_requires_a_simulation_run():
    with pytest.raises(TypeError, match="SimulationRun"):
        DecisionReport("not a run", {"profit": object()})


def test_report_rejects_mismatched_outcome_metric_name():
    summary = OutcomeSummary("revenue", 1, 1, 1, 1, 1, 0)
    with pytest.raises(ValueError, match="Outcome keys"):
        DecisionReport(fixed_run(), {"profit": summary})


@pytest.mark.parametrize(
    "keyword, value, message",
    [
        ("scenario_comparison", "bad", "ScenarioComparison"),
        ("sensitivities", ("bad",), "SensitivityResult"),
        ("affected_fields", ("profit", "profit"), "must be unique"),
        ("impact_paths", ("bad",), "ImpactPath"),
        ("critiques", "bad", "CritiqueCollection"),
        ("key_risks", ("",), "non-empty"),
        ("key_risks", ("risk", "risk"), "must be unique"),
    ],
)
def test_report_rejects_invalid_optional_sections(keyword, value, message):
    arguments = {keyword: value}
    with pytest.raises((TypeError, ValueError), match=message):
        build_decision_report(fixed_run(), **arguments)


def test_report_rejects_duplicate_sensitivity_outcomes():
    run = run_simulation(
        Decision("Test"),
        [Assumption("x", distribution=NormalDistribution(1, 0.1))],
        lambda values: {"profit": values["x"]},
        trials=10,
        seed=1,
    )
    sensitivity = analyze_sensitivity(run, "profit")
    with pytest.raises(ValueError, match="one sensitivity"):
        build_decision_report(run, sensitivities=(sensitivity, sensitivity))


def test_report_rejects_scenario_metrics_that_do_not_match():
    run = fixed_run()
    comparison = compare_scenarios(
        run.decision,
        [Assumption("x", 1)],
        lambda values: {"revenue": values["x"]},
        [Scenario("baseline")],
        "baseline",
        trials=1,
    )
    with pytest.raises(ValueError, match="Scenario metrics"):
        build_decision_report(run, scenario_comparison=comparison)

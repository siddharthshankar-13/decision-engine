"""Cross-module regression tests for the current MVP engine workflow."""

from critique import CriticDomain, CritiqueContext
from critique_adapters import (
    CallableCritiqueProvider,
    FinanceCriticAdapter,
    OperationsCriticAdapter,
    SalesCriticAdapter,
)
from critique_aggregation import aggregate_critiques
from graph import build_pricing_graph
from report import ImpactPath, build_decision_report
from scenarios import Scenario, compare_scenarios
from sensitivity import analyze_sensitivity
from simulation import (
    Assumption,
    Decision,
    NormalDistribution,
    pricing_model,
    run_simulation,
)


def test_pricing_decision_flows_through_the_complete_engine():
    decision = Decision(
        "Raise Core price 10%",
        changes={"product.price": 0.10},
    )
    assumptions = (
        Assumption("price", 100),
        Assumption("customers", 10_000),
        Assumption("elasticity", distribution=NormalDistribution(-1.2, 0.1)),
        Assumption("churn", distribution=NormalDistribution(0.04, 0.01)),
        Assumption("price_increase", 0.10),
        Assumption("variable_cost", 25),
    )
    run = run_simulation(
        decision, assumptions, pricing_model, trials=1_000, seed=42
    )
    comparison = compare_scenarios(
        decision,
        assumptions,
        pricing_model,
        (
            Scenario("expected"),
            Scenario(
                "stress",
                (
                    Assumption(
                        "elasticity", distribution=NormalDistribution(-2.0, 0.1)
                    ),
                ),
            ),
        ),
        baseline="expected",
        trials=1_000,
        seed=42,
    )
    sensitivity = analyze_sensitivity(run, "profit")

    def provider_response(payload):
        metric = {
            "finance": "profit",
            "sales": "revenue",
            "operations": "cost",
        }[payload["critic_domain"]]
        return {
            "objection": f"Review modeled {metric} downside.",
            "evidence": [
                {
                    "metric": metric,
                    "statistic": "p10",
                    "value": payload["simulation"]["p10"][metric],
                }
            ],
            "severity": "medium",
            "confidence": 0.8,
            "key_assumption": "elasticity",
        }

    provider = CallableCritiqueProvider(provider_response)
    context = CritiqueContext.from_run(
        run,
        affected_fields=(
            "product.price",
            "customers.count",
            "financials.revenue",
            "financials.cost",
            "financials.profit",
        ),
    )
    critiques = aggregate_critiques(
        context,
        (
            FinanceCriticAdapter(provider),
            SalesCriticAdapter(provider),
            OperationsCriticAdapter(provider),
        ),
    )
    path = ImpactPath(
        (
            "product.price",
            "customers.count",
            "financials.revenue",
            "financials.profit",
        )
    )
    report = build_decision_report(
        run,
        scenario_comparison=comparison,
        sensitivities=(sensitivity,),
        affected_fields=context.affected_fields,
        impact_paths=(path,),
        critiques=critiques,
        key_risks=("Demand may be more elastic than expected.",),
    )

    graph = build_pricing_graph()
    assert all(graph.get_field(reference) for reference in report.affected_fields)
    assert set(report.outcomes) == {"profit", "cost", "revenue"}
    assert report.outcomes["profit"].p10 == run.result.p10["profit"]
    assert comparison.p50_deltas["stress"]["profit"] < 0
    assert sensitivity.scores[0].assumption in {"elasticity", "churn"}
    assert set(critiques.by_domain) == set(CriticDomain)
    assert report.impact_paths == (path,)


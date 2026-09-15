import pytest

from critique import (
    Critic,
    CriticDomain,
    Critique,
    CritiqueContext,
    CritiqueEvidence,
    CritiqueSeverity,
)
from simulation import Assumption, Decision, SimulationResult, run_simulation


def build_context() -> CritiqueContext:
    run = run_simulation(
        Decision("Raise price", changes={"product.price": 0.1}),
        [Assumption("price", 110), Assumption("customers", 9000)],
        lambda values: {"revenue": values["price"] * values["customers"]},
        trials=2,
        seed=7,
    )
    return CritiqueContext.from_run(
        run,
        affected_fields=("product.price", "financials.revenue"),
        metadata={"scenario": "expected"},
    )


def test_context_is_created_from_simulation_run():
    context = build_context()
    assert context.decision.name == "Raise price"
    assert [item.name for item in context.assumptions] == ["price", "customers"]
    assert context.simulation_result.p50["revenue"] == 990_000
    assert context.affected_fields == ("product.price", "financials.revenue")


def test_context_rejects_duplicate_affected_fields():
    context = build_context()
    with pytest.raises(ValueError, match="affected_fields must be unique"):
        CritiqueContext(
            context.decision,
            context.assumptions,
            context.simulation_result,
            ("financials.revenue", "financials.revenue"),
        )


def test_critique_requires_evidence_and_bounded_confidence():
    with pytest.raises(ValueError, match="at least one"):
        Critique(
            CriticDomain.FINANCE,
            "Profit downside is material.",
            (),
            CritiqueSeverity.HIGH,
            0.9,
        )


def test_evidence_must_be_finite():
    with pytest.raises(ValueError, match="finite"):
        CritiqueEvidence("profit", "p10", float("nan"))
    with pytest.raises(ValueError, match="between 0 and 1"):
        Critique(
            CriticDomain.FINANCE,
            "Profit downside is material.",
            (CritiqueEvidence("profit", "p10", -100_000),),
            CritiqueSeverity.HIGH,
            1.1,
        )


def test_structured_critique_captures_one_objection_and_result_evidence():
    critique = Critique(
        domain=CriticDomain.FINANCE,
        objection="Revenue downside is larger than expected.",
        evidence=(CritiqueEvidence("revenue", "p10", 850_000),),
        severity=CritiqueSeverity.HIGH,
        confidence=0.82,
        key_assumption="customers",
    )
    assert critique.evidence[0].statistic == "p10"
    assert critique.key_assumption == "customers"


def test_provider_specific_critic_can_implement_the_interface():
    class FixedFinanceCritic:
        domain = CriticDomain.FINANCE

        def critique(self, context: CritiqueContext) -> Critique:
            return Critique(
                self.domain,
                "Revenue concentration creates downside risk.",
                (
                    CritiqueEvidence(
                        "revenue", "p10", context.simulation_result.p10["revenue"]
                    ),
                ),
                CritiqueSeverity.MEDIUM,
                0.75,
                "customers",
            )

    critic = FixedFinanceCritic()
    assert isinstance(critic, Critic)
    result = critic.critique(build_context())
    assert result.domain is CriticDomain.FINANCE
    assert result.evidence[0].metric == "revenue"


@pytest.mark.parametrize(
    "factory, error",
    [
        (lambda context: CritiqueContext("not a decision", (), context.simulation_result), TypeError),
        (lambda context: CritiqueContext(context.decision, ("bad",), context.simulation_result), TypeError),
        (
            lambda context: CritiqueContext(
                context.decision,
                (Assumption("x", 1), Assumption("x", 2)),
                context.simulation_result,
            ),
            ValueError,
        ),
        (lambda context: CritiqueContext(context.decision, (), "bad result"), TypeError),
        (
            lambda context: CritiqueContext(
                context.decision, context.assumptions, context.simulation_result, (" ",)
            ),
            ValueError,
        ),
    ],
)
def test_context_rejects_invalid_domain_data(factory, error):
    with pytest.raises(error):
        factory(build_context())


def test_context_from_run_requires_a_typed_run():
    with pytest.raises(TypeError, match="SimulationRun"):
        CritiqueContext.from_run("not a run")


@pytest.mark.parametrize(
    "args, error",
    [
        (("", "p10", 1), ValueError),
        (("profit", "", 1), ValueError),
        (("profit", "p10", "high"), TypeError),
    ],
)
def test_evidence_rejects_invalid_fields(args, error):
    with pytest.raises(error):
        CritiqueEvidence(*args)


@pytest.mark.parametrize(
    "changes, error",
    [
        ({"domain": "finance"}, TypeError),
        ({"objection": " "}, ValueError),
        ({"evidence": ("raw",)}, TypeError),
        ({"severity": "high"}, TypeError),
        ({"key_assumption": " "}, ValueError),
    ],
)
def test_critique_rejects_unstructured_fields(changes, error):
    values = {
        "domain": CriticDomain.FINANCE,
        "objection": "Profit downside is material.",
        "evidence": (CritiqueEvidence("profit", "p10", -1),),
        "severity": CritiqueSeverity.HIGH,
        "confidence": 0.8,
        "key_assumption": "churn",
    }
    values.update(changes)
    with pytest.raises(error):
        Critique(**values)

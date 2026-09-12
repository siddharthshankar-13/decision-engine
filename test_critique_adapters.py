import pytest

from critique import CriticDomain, CritiqueSeverity
from critique_adapters import (
    CallableCritiqueProvider,
    FinanceCriticAdapter,
    OperationsCriticAdapter,
    SalesCriticAdapter,
    build_critique_payload,
    parse_critique_response,
)
from simulation import Assumption, Decision, NormalDistribution, run_simulation
from critique import CritiqueContext


def build_context() -> CritiqueContext:
    run = run_simulation(
        Decision("Raise price", "Raise Core price 10%", {"product.price": 0.1}),
        [
            Assumption("price", 100),
            Assumption("elasticity", distribution=NormalDistribution(-1.2, 0.1)),
        ],
        lambda values: {"revenue": values["price"] * (1 + values["elasticity"] / 10)},
        trials=10,
        seed=42,
    )
    return CritiqueContext.from_run(run, ("product.price", "financials.revenue"))


def valid_response(**overrides):
    response = {
        "objection": "Revenue downside is material.",
        "evidence": [{"metric": "revenue", "statistic": "p10", "value": 85.0}],
        "severity": "high",
        "confidence": 0.8,
        "key_assumption": "elasticity",
    }
    response.update(overrides)
    return response


def test_payload_contains_summaries_but_not_raw_trials():
    payload = build_critique_payload(build_context(), CriticDomain.FINANCE)
    assert payload["critic_domain"] == "finance"
    assert payload["simulation"]["trials"] == 10
    assert "outcomes" not in payload["simulation"]
    assert payload["assumptions"][1]["distribution"] == {
        "type": "normal",
        "mean": -1.2,
        "std": 0.1,
    }


def test_payload_rejects_non_json_context():
    context = build_context()
    invalid = CritiqueContext(
        context.decision,
        context.assumptions,
        context.simulation_result,
        metadata={"value": object()},
    )
    with pytest.raises(ValueError, match="JSON-serializable"):
        build_critique_payload(invalid, CriticDomain.FINANCE)


def test_structured_response_is_parsed_for_requested_domain():
    result = parse_critique_response(CriticDomain.SALES, valid_response())
    assert result.domain is CriticDomain.SALES
    assert result.severity is CritiqueSeverity.HIGH
    assert result.evidence[0].metric == "revenue"


@pytest.mark.parametrize(
    "response, message",
    [
        ({"objection": "missing fields"}, "missing fields"),
        (valid_response(extra="not allowed"), "unknown fields"),
        (valid_response(severity="critical"), "Unknown critique severity"),
        (valid_response(evidence="not a list"), "must be a list"),
    ],
)
def test_malformed_provider_responses_are_rejected(response, message):
    with pytest.raises((TypeError, ValueError), match=message):
        parse_critique_response(CriticDomain.FINANCE, response)


def test_all_domain_adapters_use_the_same_provider_boundary():
    requested_domains = []

    def respond(payload):
        requested_domains.append(payload["critic_domain"])
        return valid_response()

    provider = CallableCritiqueProvider(respond)
    context = build_context()
    adapters = (
        FinanceCriticAdapter(provider),
        SalesCriticAdapter(provider),
        OperationsCriticAdapter(provider),
    )
    results = [adapter.critique(context) for adapter in adapters]
    assert requested_domains == ["finance", "sales", "operations"]
    assert [item.domain for item in results] == list(CriticDomain)

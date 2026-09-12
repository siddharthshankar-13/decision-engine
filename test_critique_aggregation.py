import pytest

from critique import (
    CriticDomain,
    Critique,
    CritiqueContext,
    CritiqueEvidence,
    CritiqueSeverity,
)
from critique_aggregation import CritiqueCollection, aggregate_critiques
from simulation import Assumption, Decision, run_simulation


def build_context():
    run = run_simulation(
        Decision("Test decision"),
        [Assumption("x", 1)],
        lambda values: {"profit": values["x"]},
        trials=1,
        seed=1,
    )
    return CritiqueContext.from_run(run)


def make_critique(domain, severity=CritiqueSeverity.MEDIUM, confidence=0.7):
    return Critique(
        domain,
        f"{domain.value} objection",
        (CritiqueEvidence("profit", "p10", 1),),
        severity,
        confidence,
    )


class FixedCritic:
    def __init__(self, domain, result=None):
        self.domain = domain
        self.result = result or make_critique(domain)
        self.calls = 0

    def critique(self, context):
        self.calls += 1
        return self.result


def test_aggregate_runs_each_domain_once_and_supports_lookup():
    critics = [FixedCritic(domain) for domain in CriticDomain]
    result = aggregate_critiques(build_context(), critics)
    assert len(result.critiques) == 3
    assert all(critic.calls == 1 for critic in critics)
    assert result.by_domain[CriticDomain.FINANCE].objection == "finance objection"


def test_strongest_prefers_severity_then_confidence():
    collection = CritiqueCollection(
        (
            make_critique(CriticDomain.FINANCE, CritiqueSeverity.MEDIUM, 0.99),
            make_critique(CriticDomain.SALES, CritiqueSeverity.HIGH, 0.6),
            make_critique(CriticDomain.OPERATIONS, CritiqueSeverity.HIGH, 0.8),
        )
    )
    assert collection.strongest.domain is CriticDomain.OPERATIONS


def test_empty_collection_has_no_strongest_critique():
    assert CritiqueCollection(()).strongest is None


def test_duplicate_critic_domains_are_rejected_before_execution():
    critics = [FixedCritic(CriticDomain.FINANCE), FixedCritic(CriticDomain.FINANCE)]
    with pytest.raises(ValueError, match="one critic"):
        aggregate_critiques(build_context(), critics)
    assert all(critic.calls == 0 for critic in critics)


def test_critic_must_return_its_own_domain():
    critic = FixedCritic(
        CriticDomain.FINANCE, make_critique(CriticDomain.SALES)
    )
    with pytest.raises(ValueError, match="finance critic returned a sales"):
        aggregate_critiques(build_context(), [critic])


def test_critic_must_return_structured_result():
    critic = FixedCritic(CriticDomain.FINANCE)
    critic.result = {"objection": "unvalidated"}
    with pytest.raises(TypeError, match="must return a Critique"):
        aggregate_critiques(build_context(), [critic])


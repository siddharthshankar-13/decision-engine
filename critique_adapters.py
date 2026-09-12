"""Provider adapters for structured decision critiques.

Providers receive compact, JSON-compatible summaries rather than raw Monte
Carlo outcomes.  A provider can wrap any LLM SDK; the engine only requires the
small protocol declared here.
"""

from collections.abc import Callable
from dataclasses import dataclass
import json
from typing import Any, Mapping, Protocol

from critique import (
    CriticDomain,
    Critique,
    CritiqueContext,
    CritiqueEvidence,
    CritiqueSeverity,
)


class CritiqueProvider(Protocol):
    """External boundary capable of returning one structured critique."""

    def request_critique(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class CallableCritiqueProvider:
    """Adapt a function, SDK wrapper, or test double to ``CritiqueProvider``."""

    request: Callable[[Mapping[str, Any]], Mapping[str, Any]]

    def request_critique(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return self.request(payload)


def build_critique_payload(
    context: CritiqueContext, domain: CriticDomain
) -> dict[str, Any]:
    """Build the compact provider payload shared by every critic domain."""
    if not isinstance(context, CritiqueContext):
        raise TypeError("context must be a CritiqueContext")
    if not isinstance(domain, CriticDomain):
        raise TypeError("domain must be a CriticDomain")

    assumptions = []
    for assumption in context.assumptions:
        item: dict[str, Any] = {"name": assumption.name}
        if assumption.distribution is None:
            item["value"] = assumption.value
        else:
            item["distribution"] = {
                "type": "normal",
                "mean": assumption.distribution.mean,
                "std": assumption.distribution.std,
            }
        assumptions.append(item)

    result = context.simulation_result
    payload = {
        "critic_domain": domain.value,
        "decision": {
            "name": context.decision.name,
            "description": context.decision.description,
            "changes": dict(context.decision.changes),
        },
        "assumptions": assumptions,
        "simulation": {
            "trials": result.trials,
            "seed": result.seed,
            "p10": dict(result.p10),
            "p50": dict(result.p50),
            "p90": dict(result.p90),
        },
        "affected_fields": list(context.affected_fields),
        "metadata": dict(context.metadata or {}),
        "response_contract": {
            "objection": "non-empty string",
            "evidence": [
                {"metric": "string", "statistic": "string", "value": "number"}
            ],
            "severity": [item.value for item in CritiqueSeverity],
            "confidence": "number from 0 to 1",
            "key_assumption": "optional string",
        },
    }
    try:
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("Critique context must be JSON-serializable") from error
    return payload


def parse_critique_response(
    domain: CriticDomain, response: Mapping[str, Any]
) -> Critique:
    """Validate a provider response and convert it into domain objects."""
    if not isinstance(domain, CriticDomain):
        raise TypeError("domain must be a CriticDomain")
    if not isinstance(response, Mapping):
        raise TypeError("Critique provider response must be a mapping")

    required = {"objection", "evidence", "severity", "confidence"}
    allowed = required | {"key_assumption"}
    missing = required - set(response)
    extra = set(response) - allowed
    if missing:
        raise ValueError(f"Critique response is missing fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"Critique response has unknown fields: {sorted(extra)}")

    raw_evidence = response["evidence"]
    if not isinstance(raw_evidence, (list, tuple)):
        raise TypeError("Critique evidence must be a list")
    evidence = []
    for item in raw_evidence:
        if not isinstance(item, Mapping):
            raise TypeError("Each evidence item must be a mapping")
        expected = {"metric", "statistic", "value"}
        if set(item) != expected:
            raise ValueError(
                "Evidence items require exactly metric, statistic, and value"
            )
        evidence.append(
            CritiqueEvidence(item["metric"], item["statistic"], item["value"])
        )

    try:
        severity = CritiqueSeverity(response["severity"])
    except (TypeError, ValueError) as error:
        raise ValueError("Unknown critique severity") from error

    return Critique(
        domain=domain,
        objection=response["objection"],
        evidence=tuple(evidence),
        severity=severity,
        confidence=response["confidence"],
        key_assumption=response.get("key_assumption"),
    )


@dataclass(frozen=True)
class StructuredCriticAdapter:
    """Turn a structured-output provider into a domain critic."""

    domain: CriticDomain
    provider: CritiqueProvider

    def __post_init__(self) -> None:
        if not isinstance(self.domain, CriticDomain):
            raise TypeError("domain must be a CriticDomain")
        if not callable(getattr(self.provider, "request_critique", None)):
            raise TypeError("provider must implement request_critique")

    def critique(self, context: CritiqueContext) -> Critique:
        payload = build_critique_payload(context, self.domain)
        response = self.provider.request_critique(payload)
        return parse_critique_response(self.domain, response)


class FinanceCriticAdapter(StructuredCriticAdapter):
    def __init__(self, provider: CritiqueProvider) -> None:
        super().__init__(CriticDomain.FINANCE, provider)


class SalesCriticAdapter(StructuredCriticAdapter):
    def __init__(self, provider: CritiqueProvider) -> None:
        super().__init__(CriticDomain.SALES, provider)


class OperationsCriticAdapter(StructuredCriticAdapter):
    def __init__(self, provider: CritiqueProvider) -> None:
        super().__init__(CriticDomain.OPERATIONS, provider)

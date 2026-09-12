"""Structured contracts for domain-specific decision critiques.

This module deliberately contains no LLM provider or prompt execution.  It
defines the data an eventual critic receives, the response it must return, and
the interfaces implemented by finance, sales, and operations critics.
"""

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Any, Literal, Mapping, Protocol, runtime_checkable

from simulation import Assumption, Decision, SimulationResult, SimulationRun


class CriticDomain(str, Enum):
    FINANCE = "finance"
    SALES = "sales"
    OPERATIONS = "operations"


class CritiqueSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class CritiqueContext:
    """Quantitative and graph context supplied to every critic."""

    decision: Decision
    assumptions: tuple[Assumption, ...]
    simulation_result: SimulationResult
    affected_fields: tuple[str, ...] = ()
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, Decision):
            raise TypeError("decision must be a Decision")
        assumptions = tuple(self.assumptions)
        if any(not isinstance(item, Assumption) for item in assumptions):
            raise TypeError("assumptions must contain Assumption objects")
        if len({item.name for item in assumptions}) != len(assumptions):
            raise ValueError("Assumption names must be unique")
        if not isinstance(self.simulation_result, SimulationResult):
            raise TypeError("simulation_result must be a SimulationResult")
        affected_fields = tuple(self.affected_fields)
        if any(not isinstance(item, str) or not item.strip() for item in affected_fields):
            raise ValueError("affected_fields must contain non-empty field references")
        if len(set(affected_fields)) != len(affected_fields):
            raise ValueError("affected_fields must be unique")
        object.__setattr__(self, "assumptions", assumptions)
        object.__setattr__(self, "affected_fields", affected_fields)

    @classmethod
    def from_run(
        cls,
        run: SimulationRun,
        affected_fields: tuple[str, ...] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> "CritiqueContext":
        if not isinstance(run, SimulationRun):
            raise TypeError("run must be a SimulationRun")
        return cls(
            decision=run.decision,
            assumptions=run.assumptions,
            simulation_result=run.result,
            affected_fields=affected_fields,
            metadata=metadata,
        )


@dataclass(frozen=True)
class CritiqueEvidence:
    """One result-backed fact supporting a critic's objection."""

    metric: str
    statistic: str
    value: float

    def __post_init__(self) -> None:
        if not isinstance(self.metric, str) or not self.metric.strip():
            raise ValueError("Evidence metric must be a non-empty string")
        if not isinstance(self.statistic, str) or not self.statistic.strip():
            raise ValueError("Evidence statistic must be a non-empty string")
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise TypeError("Evidence value must be numeric")
        if not isfinite(self.value):
            raise ValueError("Evidence value must be finite")
        object.__setattr__(self, "value", float(self.value))


@dataclass(frozen=True)
class Critique:
    """A critic's single strongest objection to a modeled decision."""

    domain: CriticDomain
    objection: str
    evidence: tuple[CritiqueEvidence, ...]
    severity: CritiqueSeverity
    confidence: float
    key_assumption: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.domain, CriticDomain):
            raise TypeError("domain must be a CriticDomain")
        if not isinstance(self.objection, str) or not self.objection.strip():
            raise ValueError("Critique objection must be a non-empty string")
        evidence = tuple(self.evidence)
        if not evidence:
            raise ValueError("A critique requires at least one piece of evidence")
        if any(not isinstance(item, CritiqueEvidence) for item in evidence):
            raise TypeError("evidence must contain CritiqueEvidence objects")
        if not isinstance(self.severity, CritiqueSeverity):
            raise TypeError("severity must be a CritiqueSeverity")
        if (
            not isinstance(self.confidence, (int, float))
            or isinstance(self.confidence, bool)
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be a number between 0 and 1")
        if self.key_assumption is not None and (
            not isinstance(self.key_assumption, str) or not self.key_assumption.strip()
        ):
            raise ValueError("key_assumption must be a non-empty string when provided")
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "confidence", float(self.confidence))


@runtime_checkable
class Critic(Protocol):
    """Provider-independent interface implemented by every domain critic."""

    domain: CriticDomain

    def critique(self, context: CritiqueContext) -> Critique:
        """Return the domain's single strongest evidence-backed objection."""
        ...


class FinanceCritic(Critic, Protocol):
    """Interface for critiques focused on financial outcomes and risk."""

    domain: Literal[CriticDomain.FINANCE]


class SalesCritic(Critic, Protocol):
    """Interface for critiques focused on customers, demand, and revenue."""

    domain: Literal[CriticDomain.SALES]


class OperationsCritic(Critic, Protocol):
    """Interface for critiques focused on cost and operational effects."""

    domain: Literal[CriticDomain.OPERATIONS]

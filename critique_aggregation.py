"""Validation and aggregation for domain-specific critiques."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from critique import Critic, CriticDomain, Critique, CritiqueContext, CritiqueSeverity


_SEVERITY_RANK = {
    CritiqueSeverity.LOW: 1,
    CritiqueSeverity.MEDIUM: 2,
    CritiqueSeverity.HIGH: 3,
}


@dataclass(frozen=True)
class CritiqueCollection:
    critiques: tuple[Critique, ...]

    def __post_init__(self) -> None:
        critiques = tuple(self.critiques)
        if any(not isinstance(item, Critique) for item in critiques):
            raise TypeError("critiques must contain Critique objects")
        domains = [item.domain for item in critiques]
        if len(set(domains)) != len(domains):
            raise ValueError("Only one critique is allowed per domain")
        object.__setattr__(self, "critiques", critiques)

    @property
    def by_domain(self) -> Mapping[CriticDomain, Critique]:
        return MappingProxyType({item.domain: item for item in self.critiques})

    @property
    def strongest(self) -> Critique | None:
        if not self.critiques:
            return None
        return max(
            self.critiques,
            key=lambda item: (_SEVERITY_RANK[item.severity], item.confidence),
        )


def aggregate_critiques(
    context: CritiqueContext, critics: Sequence[Critic]
) -> CritiqueCollection:
    """Run critics once and validate ownership of every returned objection."""
    if not isinstance(context, CritiqueContext):
        raise TypeError("context must be a CritiqueContext")
    critics = tuple(critics)
    for critic in critics:
        if not isinstance(critic, Critic):
            raise TypeError("critics must implement the Critic interface")
        if not isinstance(critic.domain, CriticDomain):
            raise TypeError("critic domain must be a CriticDomain")
    domains = [critic.domain for critic in critics]
    if len(set(domains)) != len(domains):
        raise ValueError("Only one critic is allowed per domain")

    critiques = []
    for critic in critics:
        critique = critic.critique(context)
        if not isinstance(critique, Critique):
            raise TypeError("A critic must return a Critique")
        if critique.domain is not critic.domain:
            raise ValueError(
                f"{critic.domain.value} critic returned a {critique.domain.value} critique"
            )
        critiques.append(critique)
    return CritiqueCollection(tuple(critiques))


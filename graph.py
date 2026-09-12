"""Structural graph model for representing decision systems."""

from dataclasses import dataclass, field
from typing import Any

def _validate_name(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")

def _validate_references(values: tuple[str, ...], label: str) -> None:
    if not values or any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{label} must contain at least one non-empty string")

@dataclass
class Field:
    name: str
    value: Any = None

    def __post_init__(self) -> None:
        _validate_name(self.name, "Field name")

@dataclass
class Node:
    name: str
    fields: dict[str, Field] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_name(self.name, "Node name")

    def add_field(self, field: Field) -> Field:
        if field.name in self.fields:
            raise ValueError(f"Field already exists on node {self.name!r}: {field.name!r}")
        self.fields[field.name] = field
        return field

    def get_field(self, name: str) -> Field:
        return self.fields[name]

@dataclass
class Dependency:
    name: str
    sources: tuple[str, ...]
    target: str
    transformation: Any = None

    def __post_init__(self) -> None:
        if isinstance(self.sources, (str, bytes)):
            raise ValueError("Dependency sources must be a sequence of field references")
        self.sources = tuple(self.sources)
        _validate_name(self.name, "Dependency name")
        _validate_references(self.sources, "Dependency sources")
        _validate_name(self.target, "Dependency target")

@dataclass
class Constraint:
    name: str
    affected_fields: tuple[str, ...]
    rule: Any = None

    def __post_init__(self) -> None:
        if isinstance(self.affected_fields, (str, bytes)):
            raise ValueError("Constraint affected_fields must be a sequence of field references")
        self.affected_fields = tuple(self.affected_fields)
        _validate_name(self.name, "Constraint name")
        _validate_references(self.affected_fields, "Constraint affected_fields")


@dataclass(frozen=True)
class ConstraintViolation:
    """A failed executable constraint and the values that caused it."""

    constraint_name: str
    affected_fields: tuple[str, ...]
    values: tuple[Any, ...]

@dataclass
class Graph:
    name: str
    nodes: dict[str, Node] = field(default_factory=dict)
    dependencies: dict[str, Dependency] = field(default_factory=dict)
    constraints: dict[str, Constraint] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_name(self.name, "Graph name")

    def add_node(self, node: Node) -> Node:
        if node.name in self.nodes:
            raise ValueError(f"Node already exists: {node.name!r}")
        self.nodes[node.name] = node
        return node

    def get_node(self, name: str) -> Node:
        return self.nodes[name]

    def get_field(self, reference: str) -> Field:
        """Retrieve a field using the canonical ``node.field`` reference."""
        if not isinstance(reference, str) or reference.count(".") != 1:
            raise ValueError("Field reference must have the form 'node.field'")
        node_name, field_name = reference.split(".")
        if not node_name or not field_name:
            raise ValueError("Field reference must have the form 'node.field'")
        return self.get_node(node_name).get_field(field_name)

    def add_dependency(self, dependency: Dependency) -> Dependency:
        if dependency.name in self.dependencies:
            raise ValueError(f"Dependency already exists: {dependency.name!r}")
        self.dependencies[dependency.name] = dependency
        return dependency

    def get_dependency(self, name: str) -> Dependency:
        return self.dependencies[name]

    def add_constraint(self, constraint: Constraint) -> Constraint:
        if constraint.name in self.constraints:
            raise ValueError(f"Constraint already exists: {constraint.name!r}")
        self.constraints[constraint.name] = constraint
        return constraint

    def get_constraint(self, name: str) -> Constraint:
        return self.constraints[name]

    def evaluate_constraint(self, name: str) -> ConstraintViolation | None:
        """Evaluate one callable constraint and return its violation, if any."""
        constraint = self.get_constraint(name)
        if not callable(constraint.rule):
            raise TypeError("Constraint rule is not executable")
        values = tuple(self.get_field(reference).value for reference in constraint.affected_fields)
        if constraint.rule(*values):
            return None
        return ConstraintViolation(constraint.name, constraint.affected_fields, values)

    def evaluate_constraints(self) -> list[ConstraintViolation]:
        """Evaluate all executable constraints, leaving opaque rules structural."""
        violations = []
        for constraint in self.constraints.values():
            if callable(constraint.rule):
                violation = self.evaluate_constraint(constraint.name)
                if violation is not None:
                    violations.append(violation)
        return violations

    def execute_dependency(self, name: str) -> Any:
        """Execute one dependency when its transformation is callable."""
        dependency = self.get_dependency(name)
        if not callable(dependency.transformation):
            raise TypeError("Dependency transformation is not executable")
        values = [self.get_field(reference).value for reference in dependency.sources]
        result = dependency.transformation(*values)
        self.get_field(dependency.target).value = result
        return result

    def propagate(self) -> None:
        """Execute callable dependencies in dependency order, detecting cycles."""
        pending = {
            name for name, dependency in self.dependencies.items()
            if callable(dependency.transformation)
        }
        producers = {
            dependency.target: name
            for name, dependency in self.dependencies.items()
            if callable(dependency.transformation)
        }
        prerequisites = {
            name: {
                producers[source]
                for source in self.dependencies[name].sources
                if source in producers
            }
            for name in pending
        }
        completed = set()
        while pending:
            progressed = False
            for name in tuple(pending):
                dependency = self.dependencies[name]
                if prerequisites[name] <= completed and all(
                    self.get_field(reference).value is not None
                    for reference in dependency.sources
                ):
                    self.execute_dependency(name)
                    pending.remove(name)
                    completed.add(name)
                    progressed = True
            if not progressed:
                raise RuntimeError("Unable to propagate dependencies; missing values or a cycle exists")

def build_pricing_graph() -> Graph:
    graph = Graph("pricing")
    values = {"product": {"price": 100}, "customers": {"count": 10_000},
              "assumptions": {"elasticity": -1.2, "churn": 0.04},
              "financials": {"revenue": None, "cost": None, "profit": None}}
    for node_name, fields in values.items():
        node = graph.add_node(Node(node_name))
        for field_name, value in fields.items():
            node.add_field(Field(field_name, value))
    graph.add_dependency(Dependency("revenue", ("product.price", "customers.count", "assumptions.elasticity"), "financials.revenue", "pricing revenue relationship"))
    graph.add_dependency(Dependency("cost", ("customers.count",), "financials.cost", "pricing cost relationship"))
    graph.add_dependency(Dependency("profit", ("financials.revenue", "financials.cost"), "financials.profit", "revenue minus cost"))
    graph.add_constraint(Constraint("non_negative_price", ("product.price",), "price >= 0"))
    graph.add_constraint(Constraint("non_negative_customers", ("customers.count",), "count >= 0"))
    return graph

pricing_graph = build_pricing_graph

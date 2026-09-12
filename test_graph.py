import pytest

from graph import Constraint, ConstraintViolation, Dependency, Field, Graph, Node, build_pricing_graph

def test_ownership_and_retrieval():
    node = Node("customers")
    field = Field("count", 10_000)
    assert node.add_field(field) is field and node.get_field("count") is field
    graph = Graph("example")
    graph.add_node(node)
    dependency = graph.add_dependency(Dependency("growth", ("customers.count",), "customers.next"))
    constraint = graph.add_constraint(Constraint("valid", ("customers.count",), "count >= 0"))
    assert graph.get_node("customers") is node
    assert graph.get_dependency("growth") is dependency
    assert graph.get_constraint("valid") is constraint

def test_duplicate_names_are_rejected():
    graph = Graph("example")
    graph.add_node(Node("x"))
    with pytest.raises(ValueError): graph.add_node(Node("x"))
    node = graph.get_node("x")
    node.add_field(Field("value"))
    with pytest.raises(ValueError): node.add_field(Field("value"))
    graph.add_dependency(Dependency("d", ("x.value",), "x.output"))
    with pytest.raises(ValueError): graph.add_dependency(Dependency("d", ("x.value",), "x.output"))
    graph.add_constraint(Constraint("c", ("x.value",)))
    with pytest.raises(ValueError): graph.add_constraint(Constraint("c", ("x.value",)))

def test_structural_dependency_and_pricing_graph():
    marker = object()
    dependency = Dependency("revenue", ("price.value", "customers.count"), "revenue.value", marker)
    assert dependency.sources == ("price.value", "customers.count")
    assert dependency.transformation is marker
    with pytest.raises(ValueError): Dependency("bad", "price.value", "revenue.value")
    graph = build_pricing_graph()
    assert set(graph.nodes) == {"product", "customers", "assumptions", "financials"}
    assert len(graph.dependencies) == 3 and len(graph.constraints) == 2
    assert graph.get_node("financials").get_field("profit").value is None

def test_canonical_field_lookup_and_callable_propagation():
    graph = Graph("example")
    source = graph.add_node(Node("source"))
    target = graph.add_node(Node("target"))
    source.add_field(Field("left", 2))
    source.add_field(Field("right", 3))
    target.add_field(Field("total"))
    graph.add_dependency(Dependency("sum", ("source.left", "source.right"), "target.total", lambda left, right: left + right))
    assert graph.get_field("source.left").value == 2
    graph.propagate()
    assert graph.get_field("target.total").value == 5

def test_non_callable_transformations_remain_structural():
    graph = build_pricing_graph()
    with pytest.raises(TypeError):
        graph.execute_dependency("revenue")
    graph.propagate()
    assert graph.get_field("financials.profit").value is None

def test_propagation_orders_dependencies_and_detects_initialized_cycle():
    graph = Graph("ordered")
    node = graph.add_node(Node("values"))
    for name, value in (("source", 2), ("middle", None), ("target", None)):
        node.add_field(Field(name, value))
    graph.add_dependency(Dependency("second", ("values.middle",), "values.target", lambda value: value * 3))
    graph.add_dependency(Dependency("first", ("values.source",), "values.middle", lambda value: value + 1))
    graph.propagate()
    assert graph.get_field("values.target").value == 9

    cyclic = Graph("cyclic")
    cycle_node = cyclic.add_node(Node("values"))
    cycle_node.add_field(Field("a", 1))
    cycle_node.add_field(Field("b", 2))
    cyclic.add_dependency(Dependency("a_from_b", ("values.b",), "values.a", lambda value: value))
    cyclic.add_dependency(Dependency("b_from_a", ("values.a",), "values.b", lambda value: value))
    with pytest.raises(RuntimeError, match="cycle"):
        cyclic.propagate()

def test_constraint_evaluation_reports_violations():
    graph = Graph("example")
    node = graph.add_node(Node("product"))
    node.add_field(Field("price", -5))
    graph.add_constraint(Constraint("non_negative_price", ("product.price",), lambda price: price >= 0))
    violation = graph.evaluate_constraint("non_negative_price")
    assert violation == ConstraintViolation("non_negative_price", ("product.price",), (-5,))
    assert graph.evaluate_constraints() == [violation]

def test_passing_and_structural_constraints_are_handled():
    graph = Graph("example")
    node = graph.add_node(Node("product"))
    node.add_field(Field("price", 10))
    graph.add_constraint(Constraint("non_negative", ("product.price",), lambda price: price >= 0))
    graph.add_constraint(Constraint("placeholder", ("product.price",), "price >= 0"))
    assert graph.evaluate_constraints() == []
    with pytest.raises(TypeError):
        graph.evaluate_constraint("placeholder")

@pytest.mark.parametrize("factory", [lambda: Field(""), lambda: Node(""), lambda: Graph(""), lambda: Dependency("x", (), "a.b"), lambda: Constraint("x", ())])
def test_empty_values_are_rejected(factory):
    with pytest.raises(ValueError): factory()

@pytest.mark.parametrize("reference", ["node", ".field", "node.", "a.b.c"])
def test_invalid_canonical_references_are_rejected(reference):
    with pytest.raises(ValueError):
        Graph("example").get_field(reference)

import pytest

from src.api.routes.workflows import _topo_sort
from src.models.workflow import WorkflowEdgeModel, WorkflowNodeModel


def node(node_id: str) -> WorkflowNodeModel:
    return WorkflowNodeModel(id=node_id, agent_id="knowledge", label=node_id)


def edge(source: str, target: str) -> WorkflowEdgeModel:
    return WorkflowEdgeModel(id=f"{source}-{target}", source=source, target=target)


def test_topological_sort_orders_connected_agents():
    nodes = [node("c"), node("a"), node("b")]
    edges = [edge("a", "b"), edge("b", "c")]

    assert _topo_sort(nodes, edges) == ["a", "b", "c"]


def test_topological_sort_rejects_cycles():
    nodes = [node("a"), node("b")]

    with pytest.raises(ValueError, match="cycle"):
        _topo_sort(nodes, [edge("a", "b"), edge("b", "a")])


def test_topological_sort_rejects_dangling_edges():
    with pytest.raises(ValueError, match="existing nodes"):
        _topo_sort([node("a")], [edge("a", "missing")])


def test_topological_sort_rejects_duplicate_edges():
    nodes = [node("a"), node("b")]

    with pytest.raises(ValueError, match="Duplicate"):
        _topo_sort(nodes, [edge("a", "b"), edge("a", "b")])

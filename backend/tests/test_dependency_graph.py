import pytest

from app.agents.agent_workflows import AgentNode, DependencyGraph


def test_execution_levels_respect_dependencies():
    graph = DependencyGraph([
        AgentNode("trial_balance", None),
        AgentNode("variance", None),
        AgentNode("accrual", None, depends_on=("trial_balance",)),
        AgentNode("intercompany", None, depends_on=("accrual", "variance")),
    ])

    levels = graph.execution_levels()

    assert levels == [
        ["trial_balance", "variance"],
        ["accrual"],
        ["intercompany"],
    ]


def test_independent_agents_share_a_level():
    graph = DependencyGraph([
        AgentNode("a", None),
        AgentNode("b", None),
        AgentNode("c", None),
    ])

    levels = graph.execution_levels()

    assert len(levels) == 1
    assert sorted(levels[0]) == ["a", "b", "c"]


def test_cycle_is_detected():
    graph = DependencyGraph([
        AgentNode("a", None, depends_on=("b",)),
        AgentNode("b", None, depends_on=("a",)),
    ])

    with pytest.raises(ValueError, match="Cycle detected"):
        graph.execution_levels()


def test_unknown_dependency_raises_at_construction():
    with pytest.raises(ValueError, match="Unknown dependency"):
        DependencyGraph([AgentNode("a", None, depends_on=("ghost",))])

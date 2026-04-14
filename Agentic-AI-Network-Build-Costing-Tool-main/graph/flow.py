"""
LangGraph orchestration: Input -> Estimation -> Optimization -> Visualization -> Storage.
"""
from typing import Any, Dict, TypedDict

from langgraph.graph import StateGraph, END
from agents.crew import run_estimation_crew, run_budget_crew, run_upgrade_crew, run_maps_crew


class GraphState(TypedDict):
    inputs: Dict[str, Any]
    result: Dict[str, Any]
    error: str


def _node_estimation(state: GraphState) -> GraphState:
    result = run_estimation_crew(state["inputs"])
    return {"result": result, "error": ""}


def _node_budget(state: GraphState) -> GraphState:
    result = run_budget_crew(state["inputs"])
    return {"result": result, "error": ""}


def _node_upgrade(state: GraphState) -> GraphState:
    result = run_upgrade_crew(state["inputs"])
    return {"result": result, "error": ""}


def _node_maps(state: GraphState) -> GraphState:
    result = run_maps_crew(state["inputs"])
    return {"result": result, "error": ""}


def _node_visualization(state: GraphState) -> GraphState:
    """Ensure charts_data is present for frontend."""
    r = state.get("result") or {}
    if "charts_data" not in r and "cost_breakdown" in r:
        r["charts_data"] = {
            "breakdown_labels": list(r["cost_breakdown"].keys()),
            "breakdown_values": list(r["cost_breakdown"].values()),
        }
    return {"result": r}


def build_estimation_graph():
    g = StateGraph(GraphState)
    g.add_node("estimation", _node_estimation)
    g.add_node("visualization", _node_visualization)
    g.set_entry_point("estimation")
    g.add_edge("estimation", "visualization")
    g.add_edge("visualization", END)
    return g.compile()


def build_budget_graph():
    g = StateGraph(GraphState)
    g.add_node("budget_planning", _node_budget)
    g.add_node("visualization", _node_visualization)
    g.set_entry_point("budget_planning")
    g.add_edge("budget_planning", "visualization")
    g.add_edge("visualization", END)
    return g.compile()


def build_upgrade_graph():
    g = StateGraph(GraphState)
    g.add_node("upgrade_planning", _node_upgrade)
    g.add_node("visualization", _node_visualization)
    g.set_entry_point("upgrade_planning")
    g.add_edge("upgrade_planning", "visualization")
    g.add_edge("visualization", END)
    return g.compile()


def build_maps_graph():
    g = StateGraph(GraphState)
    g.add_node("maps_estimation", _node_maps)
    g.add_node("visualization", _node_visualization)
    g.set_entry_point("maps_estimation")
    g.add_edge("maps_estimation", "visualization")
    g.add_edge("visualization", END)
    return g.compile()


_estimation_graph = None
_budget_graph = None
_upgrade_graph = None
_maps_graph = None


def run_estimation_graph(inputs: Dict[str, Any]) -> Dict[str, Any]:
    global _estimation_graph
    if _estimation_graph is None:
        _estimation_graph = build_estimation_graph()
    final = _estimation_graph.invoke({"inputs": inputs})
    return final.get("result") or {}


def run_budget_graph(inputs: Dict[str, Any]) -> Dict[str, Any]:
    global _budget_graph
    if _budget_graph is None:
        _budget_graph = build_budget_graph()
    final = _budget_graph.invoke({"inputs": inputs})
    return final.get("result") or {}


def run_upgrade_graph(inputs: Dict[str, Any]) -> Dict[str, Any]:
    global _upgrade_graph
    if _upgrade_graph is None:
        _upgrade_graph = build_upgrade_graph()
    final = _upgrade_graph.invoke({"inputs": inputs})
    return final.get("result") or {}


def run_maps_graph(inputs: Dict[str, Any]) -> Dict[str, Any]:
    global _maps_graph
    if _maps_graph is None:
        _maps_graph = build_maps_graph()
    final = _maps_graph.invoke({"inputs": inputs})
    return final.get("result") or {}

# agent_graph.py
from langgraph.graph import StateGraph, START, END
from state import AgentState
from agents.trend_agent import trend_agent
from agents.market_agent import market_agent
from agents.cost_agent import cost_agent
from agents.strategist_agent import strategist_agent


def build_graph() -> StateGraph:
    """
    Bedülonca ajan zincirini kurar ve derlenmiş graph'ı döner.
    Akış: START → trend → market → cost → strategist → END
    """
    graph = StateGraph(AgentState)

    # Düğümleri kaydet
    graph.add_node("trend_agent",      trend_agent)
    graph.add_node("market_agent",     market_agent)
    graph.add_node("cost_agent",       cost_agent)
    graph.add_node("strategist_agent", strategist_agent)

    # Kenarları bağla (doğrusal zincir)
    graph.add_edge(START,             "trend_agent")
    graph.add_edge("trend_agent",     "market_agent")
    graph.add_edge("market_agent",    "cost_agent")
    graph.add_edge("cost_agent",      "strategist_agent")
    graph.add_edge("strategist_agent", END)

    return graph.compile()


# Modül doğrudan çalıştırıldığında graph yapısını görselleştir
if __name__ == "__main__":
    app = build_graph()
    print("✅ Graph başarıyla derlendi.")
    print(app.get_graph().draw_ascii())
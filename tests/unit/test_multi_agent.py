from app.agent import root_agent, product_advocate, competitor_analyst
from google.adk.agents import SequentialAgent

def test_multi_agent_structure():
    assert isinstance(root_agent, SequentialAgent)
    sub_agent_names = [agent.name for agent in root_agent.sub_agents]
    assert "product_advocate" in sub_agent_names
    assert "competitor_analyst" in sub_agent_names
    
    # Advocate has tools for details, catalog, and trade-in
    advocate_tool_names = [getattr(t, "name", getattr(t, "__name__", str(t))) for t in product_advocate.tools]
    assert "get_smartphone_details" in advocate_tool_names
    assert "list_smartphones" in advocate_tool_names
    assert "save_trade_in_inquiry" in advocate_tool_names
    
    # Analyst has tools for comparisons
    analyst_tool_names = [getattr(t, "name", getattr(t, "__name__", str(t))) for t in competitor_analyst.tools]
    assert "list_smartphones" in analyst_tool_names
    assert "get_smartphone_details" in analyst_tool_names
    assert "generate_comparison_image" in analyst_tool_names


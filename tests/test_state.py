import pytest
from core.state import SupportState
from langchain_core.messages import HumanMessage

def test_support_state_initialization():
    initial_state: SupportState = {
        "messages": [HumanMessage(content="Hello")],
        "ticket_category": "general",
        "needs_escalation": False,
        "escalation_summary": ""
    }
    
    assert len(initial_state["messages"]) == 1
    assert initial_state["messages"][0].content == "Hello"
    assert initial_state["ticket_category"] == "general"
    assert initial_state["needs_escalation"] == False
    assert initial_state["escalation_summary"] == ""

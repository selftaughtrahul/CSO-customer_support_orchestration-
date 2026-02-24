# agents/escalation.py
from core.llm_setup import get_llm
from core.state import SupportState
from langchain_core.messages import AIMessage

def human_escalation_node(state: SupportState):
    """Summarizes the conversation and pauses the graph execution."""
    llm = get_llm(temperature=0)
    
    # We ask the LLM to summarize the entire state['messages'] array
    prompt = f"Summarize the user's issue and why the agents failed to resolve it:\n{state['messages']}"
    summary = llm.invoke(prompt)
    
    # Alert the user that the system is paused
    alert_msg = AIMessage(content="I have escalated this ticket to a human administrator. Please hold.")
    
    return {
        "escalation_summary": summary.content,
        "needs_escalation": True,
        "messages": [alert_msg]
    }
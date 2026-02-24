from core.llm_setup import get_llm
from langgraph.prebuilt import create_react_agent

# Get the configured LLM
llm = get_llm(temperature=0.7)


def general_agent_node(state):
    """Handles standard interactions without tools."""
    llm = get_llm(temperature=0.3)
    response = llm.invoke([{"role": "system", "content": "You are a friendly general support agent."}] + state["messages"])
    
    # Return the AI response wrapped in the messages dict to append to state
    return {"messages": [response]}
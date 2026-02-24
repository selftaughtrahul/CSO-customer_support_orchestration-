from langgraph.graph import StateGraph,START, END
from core.state import SupportState

# Import modular nodes
from agents.router import router_node
from agents.general import general_agent_node
from agents.billing import billing_agent_node
from agents.tech import tech_agent_node

from agents.escalation import human_escalation_node
from langgraph_checkpoint_sqlite import SqliteSaver




# 1. Initialize the Graph
workflow = StateGraph(SupportState)

# 2. Add our modular Agents as executable Nodes
workflow.add_node("router", router_node)
workflow.add_node("general_agent", general_agent_node)
workflow.add_node("billing_agent", billing_agent_node)
workflow.add_node("tech_agent", tech_agent_node)
workflow.add_node("human_escalation", human_escalation_node)


# 3. Define the custom Routing Logic (The Switchboard)
def route_to_department(state: SupportState):
    """Inspects the 'ticket_category' string set by the router node."""
    category = state.get("ticket_category")
    needs_esc = state.get("needs_escalation")
    
    if needs_esc:
        return "human_escalation"    
    if category == "billing":
        return "billing_agent"
    elif category == "technical":
        return "tech_agent"        
    else:
        return "general_agent"
    


memory = SqliteSaver.from_conn_string("threads.sqlite")
# 4. Draw the Edges
# Every conversation starts by going to the Router LLM
workflow.add_edge(START, "router")

# The Router output determines which specialized Agent takes over
workflow.add_conditional_edges("router", route_to_department)

# After a specialized agent acts (and returns its answer/tool output) the cycle ends
workflow.add_edge("general_agent", END)
workflow.add_edge("billing_agent", END)
workflow.add_edge("tech_agent", END)

# 5. Compile the executable application
app = workflow.compile(
    checkpointer=memory,
    interrupt_before=["human_escalation"] # Graph freezes here
)


if __name__ == "__main__":
    from langchain_core.messages import HumanMessage
    
    # Send a mock ticket to test Groq/Gemini LLM functionality
    test_input = {"messages": [HumanMessage(content="Check my billing status for USER_101")]}
    final_state = app.invoke(test_input)
    
    print("Final State Dictionary:", final_state)
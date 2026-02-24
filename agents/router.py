from core.llm_setup import get_llm
from core.state import SupportState
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

# 1. Define the Output Schema (Pydantic)
class TicketClassification(BaseModel):
    """Schema for routing the support ticket."""
    category: str = Field(
        ..., 
        description="The category of the issue. Must be one of: general, billing, technical, or escalate."
    )
    needs_escalation: bool = Field(
        False, 
        description="Set to True if the issue requires a human agent immediately."
    )
    summary: str = Field(
        "", 
        description="A brief summary of the customer's problem."
    )

# 2. Create the Router Agent
def create_router_agent():
    llm = get_llm()
    
    # Bind the Pydantic schema to the LLM
    # This forces the LLM to return JSON that matches our TicketClassification model
    structured_llm = llm.with_structured_output(TicketClassification)

    system_prompt = """
You are the first-line Customer Support Router.
Your job is to analyze the customer's message and route it to the correct department.

CRITICAL RULES:
1. If the user mentions "lawyer", "legal", "sue", "complaint", or "urgent action", set needs_escalation=True immediately.
2. If the issue is about money, invoices, or payments, set category="billing".
3. If the issue is about servers, bugs, or login problems, set category="technical".
4. If the issue is a simple greeting or unclear, set category="general".
5. Always provide a brief summary of the issue.
"""

    # 3. Define the Router Node Logic
    def router_node(state: SupportState):
        # Get the latest message from the history
        latest_message = state["messages"][-1].content
        
        # Call the structured LLM
        result = structured_llm.invoke([HumanMessage(content=latest_message)])
        
        # Update the state with the routing decision
        return {
            "ticket_category": result.category,
            "needs_escalation": result.needs_escalation,
            "escalation_summary": result.summary
        }

    return router_node

# Expose the node for the graph
router_node = create_router_agent()
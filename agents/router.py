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
        description="The category of the issue. Must be one of: order, subscription, wallet, general, or escalate."
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
You are the first-line Customer Support Router for a D2C Dairy application.
Your job is to analyze the customer's message and route it to the correct department.

CRITICAL RULES:
1. If the user mentions "lawyer", "legal", "sue", "complaint", or "urgent action", set needs_escalation=True immediately.
2. If the issue is about a one-time order, order status, or when an order will be delivered, set category="order".
3. If the issue is about setting up a subscription (daily/alternate days), pausing a subscription, or checking why their scheduled daily order didn't arrive, set category="subscription".
4. If the issue is about wallet balance, recharging, ledgers, or cashback schemes, set category="wallet".
5. If the issue is a simple greeting, unclear, or a general question, set category="general".
6. Always provide a brief summary of the issue.
"""

    # 3. Define the Router Node Logic
    def router_node(state: SupportState):
        # Get the latest message from the history
        latest_message = state["messages"][-1].content
        
        # Insert system prompt context at runtime (LangGraph nodes pass only state typically, 
        # so we merge the prompt and human message here or just pass the human message)
        # We can construct the list properly:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": latest_message}
        ]
        
        # Call the structured LLM
        result = structured_llm.invoke(messages)
        
        # Update the state with the routing decision
        return {
            "ticket_category": result.category,
            "needs_escalation": result.needs_escalation,
            "escalation_summary": result.summary
        }

    return router_node

# Expose the node for the graph
router_node = create_router_agent()
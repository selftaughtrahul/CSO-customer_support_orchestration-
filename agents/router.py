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
    # ⚡ Router always uses Groq llama-3.1-8b-instant regardless of global LLM_PROVIDER
    # Fast 8B model is perfect for 5-way classification and has low token usage
    from langchain_groq import ChatGroq
    from core.config import Config
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
    )
    
    # Bind the Pydantic schema to the LLM
    # This forces the LLM to return JSON that matches our TicketClassification model
    structured_llm = llm.with_structured_output(TicketClassification)

    system_prompt = """
You are the first-line Customer Support Router for a D2C Dairy application.
Your job is to analyze the customer's message and route it to the correct department.

## ROUTING RULES:

### Route to category="order" for ANY of the following:
- Viewing, searching, listing, or fetching orders (recent, today, last N orders)
- Order status: approved, delivered, cancelled, failed, pending
- Order details, items inside an order, order code lookup
- Order tracking, delivery date, expected delivery, failed delivery
- Orders filtered by date range, today, yesterday, this week, last month
- Order analytics: total orders, order count, revenue, daily/monthly sales summary
- Product sales today, product-wise quantity, liters sold, pouches sold, free products
- Free orders, return orders, high-value orders
- Orders by town, route, hub, locality, production unit, distributor type
- Orders by vehicle number, transporter name, dispatch status
- Outstanding amount related to orders, wallet usage in orders, TCS in orders
- Top customers, top products, repeat customers, average order value
- Subscription-based orders from the order table (is_subscribed orders)
- ANY query with keywords: order, sale, deliver, dispatch, approved, cancelled,
  failed, revenue, product sold, pouches, liters, vehicle, route, town, hub,
  outstanding, amount due, order summary, analytics, sales

### Route to category="subscription" for:
- Setting up / pausing / cancelling a recurring subscription plan
- Subscription plan details, plan type (daily / alternate day / custom)
- Why a scheduled daily milk delivery did not arrive

### Route to category="wallet" for:
- Wallet balance, wallet recharge, cashback schemes, ledger entries, payment modes

### Route to category="general" ONLY for:
- Simple greetings (hello, hi, thanks, bye)
- Questions completely unrelated to orders, subscriptions, or wallet
- Company policy, FAQ, contact information

### Set needs_escalation=True if:
- User mentions "lawyer", "legal", "sue", "complaint", "consumer court", "urgent action"

## HINGLISH ROUTING GUIDE:
- "Aaj kitna sale hua" → order
- "Mera order kab aayega" → order  
- "Approved orders dikhao" → order
- "Is mahine ka revenue" → order
- "Order cancel kyun hua" → order
- "Delivered orders" → order
- "Mere subscription ka status" → subscription
- "Mera wallet balance" → wallet

Always provide a brief summary of the issue.
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
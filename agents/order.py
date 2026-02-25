from core.llm_setup import get_llm
from tools.order_tools import check_recent_orders
from langgraph.prebuilt import create_react_agent

# Get the configured LLM
llm = get_llm(temperature=0)

# Bind the tool functions 
order_tools = [check_recent_orders]

# The compiled agent node
order_agent_node = create_react_agent(
    model=llm,
    tools=order_tools,
    prompt=(
        "You are an Order Support Agent for a D2C Dairy application. "
        "Solve the customer's order-related issues (checking status, delivery dates, etc.) using your available tools ONLY. "
        "Do NOT attempt to use tools that are not explicitly provided to you. "
        "Once you have an answer from a tool, respond directly to the user to end the transaction."
    )
)

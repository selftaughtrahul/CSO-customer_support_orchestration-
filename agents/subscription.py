from core.llm_setup import get_llm
from tools.subscription_tools import check_active_subscriptions, check_subscription_logs
from langgraph.prebuilt import create_react_agent

# Get the configured LLM
llm = get_llm(temperature=0)

# Bind the tool functions 
subscription_tools = [check_active_subscriptions, check_subscription_logs]

# The compiled agent node
subscription_agent_node = create_react_agent(
    model=llm,
    tools=subscription_tools,
    prompt=(
        "You are a Subscription Support Agent for a D2C Dairy application. "
        "Solve the customer's subscription issues (checking active subscriptions, or why a scheduled order failed) using your available tools ONLY. "
        "A scheduled order might fail completely due to low wallet balance; use the logs tool to clarify the reason to the user. "
        "Do NOT attempt to use tools that are not explicitly provided to you. "
        "Once you have an answer from a tool, respond directly to the user to end the transaction."
    )
)

from core.llm_setup import get_llm
from tools.billing_tools import lookup_invoice_status, process_refund_request
from langgraph.prebuilt import create_react_agent

# Get the configured LLM
llm = get_llm(temperature=0)

# Bind the tool functions 
billing_tools = [lookup_invoice_status, process_refund_request]

# The compiled agent node
billing_agent_node = create_react_agent(
    model=llm,
    tools=billing_tools,
    prompt="You are a Billing Agent. Solve the customer's payment issues using your tools."
)
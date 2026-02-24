from core.llm_setup import get_llm
from tools.tech_tools import check_server_uptime, force_password_reset
from langgraph.prebuilt import create_react_agent

# Get the configured LLM
llm = get_llm(temperature=0)

# Bind the tool functions 
tech_tools = [check_server_uptime, force_password_reset]

# The compiled agent node
tech_agent_node = create_react_agent(
    model=llm,
    tools=tech_tools,
    prompt=(
        "You are a Technical Support Agent. Solve the customer's technical issues using your available tools ONLY. "
        "Do NOT attempt to use tools that are not explicitly provided to you (e.g. do not try to use 'brave_search'). "
        "Once you have an answer from a tool, respond directly to the user to end the transaction."
    )
)
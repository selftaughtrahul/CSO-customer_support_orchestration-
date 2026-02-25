from core.llm_setup import get_llm
from tools.wallet_tools import check_wallet_balance, get_running_schemes
from langgraph.prebuilt import create_react_agent

# Get the configured LLM
llm = get_llm(temperature=0)

# Bind the tool functions 
wallet_tools = [check_wallet_balance, get_running_schemes]

# The compiled agent node
wallet_agent_node = create_react_agent(
    model=llm,
    tools=wallet_tools,
    prompt=(
        "You are a Wallet & Schemes Support Agent for a D2C Dairy application. "
        "Solve the customer's queries about their wallet balance, ledger details, recharges, or active cashback schemes using your available tools ONLY. "
        "Do NOT attempt to use tools that are not explicitly provided to you. "
        "Once you have an answer from a tool, respond directly to the user to end the transaction."
    )
)

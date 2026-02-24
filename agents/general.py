from core.llm_setup import get_llm
from langgraph.prebuilt import create_react_agent
from tools.rag_tools import policy_search_tool


llm = get_llm(temperature=0.1)

# Compile into a ReAct agent, similar to the billing/tech agents
general_agent_node = create_react_agent(
    model=llm,
    tools=[policy_search_tool],
    prompt=(
        "You are a polite General Support Agent. "
        "Use the 'company_faq_search' tool at most ONE time to find the answer to the user's query. "
        "Do not hallucinate tools or call 'brave_search'. "
        "Once you have the information, you MUST provide a final answer directly to the user."
    )
)
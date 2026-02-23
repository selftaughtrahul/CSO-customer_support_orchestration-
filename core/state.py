# core/state.py
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

class SupportState(TypedDict):
    """The central state maintained by LangGraph."""
    # Append-only list of all user/AI/Tool messages
    messages: Annotated[Sequence[BaseMessage], operator.add]
    
    # Status tracks where the ticket is routed: general, billing, technical, escalate, resolved
    ticket_category: str
    
    # Flag to pause the graph for human intervention
    needs_escalation: bool
    
    # Summary of the issue generated before human interruption
    escalation_summary: str
# core/state.py
from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage
import operator

class SupportState(TypedDict, total=False):
    """The central state maintained by LangGraph."""
    # Append-only list of all user/AI/Tool messages — REQUIRED
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # ---------------------------------------------------------------
    # Session identity — resolved at request time from sp_users.user_type
    # user_type=1 → admin  |  user_type=4 → customer
    # Optional so old checkpoints (without these fields) don't crash
    # ---------------------------------------------------------------
    user_id: int       # logged-in user's ID
    role: str          # "admin" | "customer"

    # Router output
    ticket_category: str
    needs_escalation: bool
    escalation_summary: str
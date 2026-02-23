# tools/billing_tools.py
from langchain_core.tools import tool

@tool
def lookup_invoice_status(account_uid: str) -> str:
    """Fetch the status of the customer's last invoice."""
    # Placeholder for actual DB/Stripe query
    db = {"USER_101": "Paid", "USER_102": "Overdue ($150.00)"}
    return db.get(account_uid, f"Account {account_uid} not found. Ask for clarification.")

@tool
def process_refund_request(account_uid: str, amount: float) -> str:
    """Initiates a refund for the given account."""
    if amount > 50.0:
        return "Refunds over $50 require manager approval. Escalate to human."
    return f"Success: ${amount} refunded to account {account_uid}."
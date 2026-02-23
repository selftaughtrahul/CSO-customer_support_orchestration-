# tools/tech_tools.py
from langchain_core.tools import tool
import random

@tool
def check_server_uptime(region: str) -> str:
    """Pings the server in the specified region (e.g., 'us-east', 'eu-west')."""
    # Simulate a 10% chance the server is actually down
    if random.random() < 0.1:
        return f"CRITICAL: {region} server is DOWN. Error 503."
    return f"OK: {region} server is healthy. Uptime 99.9%."

@tool
def force_password_reset(email: str) -> str:
    """Sends a password rest link to the provided email."""
    if "@" not in email:
        return "Invalid email format."
    return f"Reset link sent to {email}. Instruct the user to check their spam folder."
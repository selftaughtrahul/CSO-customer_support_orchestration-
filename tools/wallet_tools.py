from langchain_core.tools import tool
from core.db import get_db_connection

@tool
def check_wallet_balance(user_id: int):
    """Check the latest wallet balance and recent ledger entries for a user."""
    conn = get_db_connection()
    if not conn: return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        # Check current balance (usually latest entry has the balance)
        query = "SELECT id, particulars, credit, debit, balance, posting_date FROM sp_user_ledger WHERE user_id = %s ORDER BY id DESC LIMIT 3"
        cursor.execute(query, (user_id,))
        res = cursor.fetchall()
        for row in res:
            for k, v in row.items():
                if v is not None and not isinstance(v, (int, float, str, bool)):
                    row[k] = str(v)
    except Exception as e:
        res = f"Error executing query: {e}"
    finally:
        cursor.close()
        conn.close()
        
    return res if res else f"No wallet ledger found for user_id={user_id}."

@tool
def get_running_schemes():
    """Fetch currently running schemes or offers (e.g. cashback, wallet recharge scheme)."""
    conn = get_db_connection()
    if not conn: return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        # The schema shows sp_wallet_scheme with 8 columns. If scheme_name fails we just grab all
        query = "SELECT * FROM sp_wallet_scheme WHERE status = 1 LIMIT 10"
        cursor.execute(query)
        res = cursor.fetchall()
        for row in res:
            for k, v in row.items():
                if v is not None and not isinstance(v, (int, float, str, bool)):
                    row[k] = str(v)
    except Exception as e:
        res = f"Error executing query: {e}"
    finally:
        cursor.close()
        conn.close()
        
    return res if res else "No active schemes found."

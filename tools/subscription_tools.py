from langchain_core.tools import tool
from core.db import get_db_connection

@tool
def check_active_subscriptions(user_id: int):
    """Fetch active product subscriptions for an alternate/daily milk or product user."""
    conn = get_db_connection()
    if not conn: return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT id, product_name, plan_type, status, start_date, end_date, custom_days FROM sp_subscriptions WHERE user_id = %s AND status = 1"
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
        
    return res if res else f"No active subscriptions found for user_id={user_id}."

@tool
def check_subscription_logs(user_id: int):
    """Check subscription logs if a scheduled order wasn't generated to see the reason (e.g., low wallet balance)."""
    conn = get_db_connection()
    if not conn: return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT id, action, message, log_time FROM sp_subscription_logs WHERE user_id = %s ORDER BY id DESC LIMIT 5"
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
        
    return res if res else f"No recent subscription logs found for user_id={user_id}."

from langchain_core.tools import tool
from core.db import get_db_connection

@tool
def check_recent_orders(user_id: int):
    """Fetch the 5 most recent orders for a user to check order status."""
    conn = get_db_connection()
    if not conn: return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT id, order_code, order_date, order_status, expected_delivery_date, is_subscribed FROM sp_secondary_orders WHERE user_id = %s ORDER BY id DESC LIMIT 5"
        cursor.execute(query, (user_id,))
        res = cursor.fetchall()
        
        # Convert datetime/dates to string explicitly if present
        for row in res:
            for k, v in row.items():
                if v is not None and not isinstance(v, (int, float, str, bool)):
                    row[k] = str(v)
    except Exception as e:
        res = f"Error executing query: {e}"
    finally:
        cursor.close()
        conn.close()
    
    return res if res else f"No recent orders found for user_id={user_id}."

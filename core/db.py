import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from typing import Optional

# user_type mapping from sp_users table
# 1 = Admin  |  4 = Customer
USER_TYPE_ADMIN    = 1
USER_TYPE_CUSTOMER = 4

# Load the keys, overriding any existing environment variables
load_dotenv(override=True)

def get_db_connection():
    """
    Establish a connection to the MySQL database using credentials from .env
    """
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "")
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        raise e
    
    return None


def get_user_role(user_id: int) -> str:
    """
    Resolve a user's role string by querying sp_users.user_type.

    user_type = 1  →  "admin"
    user_type = 4  →  "customer"
    Anything else  →  "customer"  (fail-safe: deny elevated access)
    """
    conn = get_db_connection()
    if not conn:
        return "customer"  # fail-safe
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT user_type FROM sp_users WHERE id = %s LIMIT 1",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            utype = row.get("user_type")
            if utype == USER_TYPE_ADMIN:
                return "admin"
            elif utype == USER_TYPE_CUSTOMER:
                return "customer"
        return "customer"  # default deny
    except Exception as e:
        print(f"[get_user_role] Error: {e}")
        return "customer"
    finally:
        cursor.close()
        conn.close()


def get_user_info(user_id: int) -> Optional[dict]:
    """
    Fetch basic profile info for a user from sp_users.
    Returns None if user is not found.
    """
    conn = get_db_connection()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, first_name, last_name, user_type, store_name, "
            "primary_contact_number, role_name "
            "FROM sp_users WHERE id = %s LIMIT 1",
            (user_id,)
        )
        return cursor.fetchone()
    except Exception as e:
        print(f"[get_user_info] Error: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    conn = get_db_connection()
    if conn:
        print("Successfully connected to the MySQL database!")
        conn.close()

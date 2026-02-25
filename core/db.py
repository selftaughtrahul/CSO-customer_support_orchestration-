import os
import mysql.connector
from mysql.connector import Error, pooling
from dotenv import load_dotenv
from typing import Optional
from functools import lru_cache

# user_type mapping from sp_users table
# 1 = Admin  |  4 = Customer
USER_TYPE_ADMIN    = 1
USER_TYPE_CUSTOMER = 4

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# Connection Pool — created ONCE at module load time
# Reuses TCP connections across all tool calls → eliminates ~200-400ms per query
# ---------------------------------------------------------------------------
_pool: Optional[pooling.MySQLConnectionPool] = None

def _get_pool() -> Optional[pooling.MySQLConnectionPool]:
    global _pool
    if _pool is None:
        try:
            _pool = pooling.MySQLConnectionPool(
                pool_name="cso_pool",
                pool_size=5,            # 5 persistent connections
                pool_reset_session=True,
                host=os.getenv("MYSQL_HOST", "localhost"),
                port=int(os.getenv("MYSQL_PORT", 3306)),
                user=os.getenv("MYSQL_USER", "root"),
                password=os.getenv("MYSQL_PASSWORD", ""),
                database=os.getenv("MYSQL_DATABASE", ""),
                connect_timeout=10,
                autocommit=True,
            )
            print("[DB] Connection pool created (size=5)")
        except Error as e:
            print(f"[DB] Pool creation failed: {e}")
            _pool = None
    return _pool


def get_db_connection():
    """
    Return a connection from the pool.
    Falls back to a direct connection if the pool is unavailable.
    """
    pool = _get_pool()
    if pool:
        try:
            return pool.get_connection()
        except Error as e:
            print(f"[DB] Pool get_connection failed: {e} — falling back to direct")

    # Fallback: direct connection (no pool)
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", ""),
            connect_timeout=10,
            autocommit=True,
        )
        return conn if conn.is_connected() else None
    except Error as e:
        print(f"[DB] Direct connection failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Role cache — avoid redundant DB lookups for the same user_id in a session
# ---------------------------------------------------------------------------
@lru_cache(maxsize=256)
def get_user_role(user_id: int) -> str:
    """
    Resolve user role from sp_users.user_type.
    Cached per user_id for the lifetime of the process.
    user_type = 1  →  'admin'
    user_type = 4  →  'customer'
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
        return "customer"
    except Exception as e:
        print(f"[get_user_role] Error: {e}")
        return "customer"
    finally:
        cursor.close()
        conn.close()   # returns connection to pool


def get_user_info(user_id: int) -> Optional[dict]:
    """
    Fetch basic profile info for a user from sp_users.
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
        print("Successfully connected to MySQL via pool!")
        conn.close()

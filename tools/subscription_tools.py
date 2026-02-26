"""
subscription_tools.py — Subscription & Vacation Support Tools
=============================================================
6 tools total:

  Subscription:
  1. check_active_subscriptions   — active plans (product, plan_type, qty, rate, dates)
  2. check_subscription_logs      — why a scheduled delivery was missed (last 10 logs)

  Vacation:
  3. get_vacation_dates            — all marked vacation dates (filter by month/year)
  4. get_upcoming_vacations        — future vacation dates (today onwards)
  5. add_vacation_date             — mark a single date as vacation (skips delivery)
  6. cancel_vacation_date          — cancel/remove a vacation date (resumes delivery)

Table: sp_customer_vacations — id, customer_name, customer_id, vacation_date, marked_by, status
Table: sp_subscriptions      — id, user_id, product_name, plan_type, quantity, rate, status, ...
Table: sp_subscription_logs  — id, subscription_id, user_id, action, message, level, log_time
"""

from langchain_core.tools import tool
from core.db import get_db_connection
from datetime import date, datetime


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _serialize(rows, array_name="data") -> str:
    """
    Serializes DB rows into TOON (Token-Oriented Object Notation).
    Eliminates repetitive JSON keys; dynamically strips entirely-null columns.
    """
    if not isinstance(rows, list) or not rows:
        return rows

    if isinstance(rows[0], dict):
        all_keys = list(rows[0].keys())
        active_keys = [
            k for k in all_keys
            if any(row.get(k) not in (None, "") for row in rows)
        ]
        length = len(rows)
        header = f"{array_name}[{length}]{{{','.join(active_keys)}}}:"
        toon_lines = [header]
        for row in rows:
            row_vals = []
            for k in active_keys:
                v = row.get(k)
                if v is None or v == "":
                    row_vals.append("null")
                elif isinstance(v, (int, float, bool)):
                    row_vals.append(str(v))
                else:
                    s = str(v).replace('"', '""')
                    row_vals.append(f'"{s}"')
            toon_lines.append(",".join(row_vals))
        return "\n".join(toon_lines)

    return rows


def _normalize_rows(rows: list) -> list:
    """Convert date/datetime objects to ISO strings so TOON serializer can handle them."""
    for row in rows:
        for k, v in row.items():
            if v is not None and not isinstance(v, (int, float, str, bool)):
                row[k] = str(v)
    return rows


# ---------------------------------------------------------------------------
# Tool 1: check_active_subscriptions
# ---------------------------------------------------------------------------

@tool
def check_active_subscriptions(user_id: int) -> str:
    """Fetch active product subscription plans for a customer.

    Returns plan details: product name, variant, plan type (daily/alternate/custom),
    plan days, quantity, rate, total amount, start date, end date, locality, and
    delivery instructions. Use this to answer 'What is my current subscription?'
    or 'Is my subscription active?'
    """
    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT
                id, product_name, product_variant_name, plan_type, plan_days,
                quantity, rate, total_amount,
                start_date, end_date, custom_days,
                locality_name, delivery_instruction, status
            FROM sp_subscriptions
            WHERE user_id = %s AND status = 1
        """
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        rows = _normalize_rows(rows)
        result = _serialize(rows, "subscriptions")
    except Exception as e:
        result = f"Error fetching subscriptions: {e}"
    finally:
        cursor.close()
        conn.close()

    return result if (result and rows) else f"No active subscriptions found for user_id={user_id}."


# ---------------------------------------------------------------------------
# Tool 2: check_subscription_logs
# ---------------------------------------------------------------------------

@tool
def check_subscription_logs(user_id: int) -> str:
    """Check recent subscription logs to diagnose why a scheduled delivery was missed.

    Common failure reasons found in logs:
    - Low wallet balance (insufficient funds)
    - Subscription expired or paused
    - System/cron error
    - Vacation day (delivery intentionally skipped)

    Returns the last 10 log entries with action, message, and timestamp.
    """
    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT id, subscription_id, action, message, level, log_time
            FROM sp_subscription_logs
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT 10
        """
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        rows = _normalize_rows(rows)
        result = _serialize(rows, "subscription_logs")
    except Exception as e:
        result = f"Error fetching subscription logs: {e}"
    finally:
        cursor.close()
        conn.close()

    return result if (result and rows) else f"No recent subscription logs found for user_id={user_id}."


# ---------------------------------------------------------------------------
# Tool 3: get_vacation_dates
# ---------------------------------------------------------------------------

@tool
def get_vacation_dates(user_id: int, month: int = None, year: int = None) -> str:
    """Fetch all active vacation dates for a customer.

    Optionally filter by month (1-12) and/or year (e.g. 2026).
    Returns vacation_date and created_at for each entry.

    Use this to answer:
    - 'Show my vacation dates'
    - 'Which days did I mark as vacation this month?'
    - 'How many vacation days do I have in March?'
    """
    params: list = [user_id]
    where = ["customer_id = %s", "status = 1"]

    if month:
        where.append("MONTH(vacation_date) = %s")
        params.append(month)
    if year:
        where.append("YEAR(vacation_date) = %s")
        params.append(year)

    query = f"""
        SELECT id, vacation_date, created_at
        FROM sp_customer_vacations
        WHERE {' AND '.join(where)}
        ORDER BY vacation_date ASC
    """
    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        rows = _normalize_rows(rows)
        result = _serialize(rows, "vacations")
    except Exception as e:
        result = f"Error fetching vacation dates: {e}"
    finally:
        cursor.close()
        conn.close()

    return result if (result and rows) else f"No vacation dates found for user_id={user_id}."


# ---------------------------------------------------------------------------
# Tool 4: get_upcoming_vacations
# ---------------------------------------------------------------------------

@tool
def get_upcoming_vacations(user_id: int) -> str:
    """Fetch upcoming (future) vacation dates for a customer — today onwards only.

    Use this to answer:
    - 'Show my upcoming vacations'
    - 'When is my next vacation?'
    - 'Will milk be delivered next week?' (check if any vacation overlaps)
    """
    today = date.today().isoformat()
    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT id, vacation_date, created_at
            FROM sp_customer_vacations
            WHERE customer_id = %s AND status = 1 AND vacation_date >= %s
            ORDER BY vacation_date ASC
        """
        cursor.execute(query, (user_id, today))
        rows = cursor.fetchall()
        rows = _normalize_rows(rows)
        result = _serialize(rows, "upcoming_vacations")
    except Exception as e:
        result = f"Error fetching upcoming vacations: {e}"
    finally:
        cursor.close()
        conn.close()

    return result if (result and rows) else f"No upcoming vacations found for user_id={user_id}."


# ---------------------------------------------------------------------------
# Tool 5: add_vacation_date
# ---------------------------------------------------------------------------

@tool
def add_vacation_date(user_id: int, vacation_date: str) -> str:
    """Mark a specific date as a vacation day — milk delivery will be SKIPPED on this date.

    vacation_date must be in YYYY-MM-DD format (e.g., '2026-03-10').

    For a date range (e.g., 'March 5th to 10th'), call this tool once per date.

    Returns a success or error message.

    Use this to answer:
    - 'Mark vacation for 10th March'
    - 'I won't be home on 2026-03-05, skip delivery'
    - 'I'm going on vacation from 5th to 8th March'
    """
    # --- Validate date format ---
    try:
        vac_date = datetime.strptime(vacation_date, "%Y-%m-%d").date()
    except ValueError:
        return (
            f"Invalid date format '{vacation_date}'. "
            "Please provide the date in YYYY-MM-DD format (e.g., '2026-03-10')."
        )

    if vac_date < date.today():
        return (
            f"Cannot mark vacation for a past date ({vacation_date}). "
            "Please provide today's date or a future date."
        )

    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        # Resolve customer name
        cursor.execute(
            "SELECT first_name, last_name, store_name FROM sp_users WHERE id = %s",
            (user_id,)
        )
        user_row = cursor.fetchone()
        if not user_row:
            return f"User not found for user_id={user_id}."

        customer_name = (
            f"{user_row.get('first_name', '')} {user_row.get('last_name', '')}".strip()
            or user_row.get("store_name", f"User_{user_id}")
        )

        # Check if a vacation entry already exists for this date
        cursor.execute(
            "SELECT id, status FROM sp_customer_vacations "
            "WHERE customer_id = %s AND vacation_date = %s",
            (user_id, vacation_date)
        )
        existing = cursor.fetchone()

        if existing:
            if existing["status"] == 1:
                return f"Vacation on {vacation_date} is already marked. No changes made."
            else:
                # Reactivate a previously cancelled entry
                cursor.execute(
                    "UPDATE sp_customer_vacations "
                    "SET status = 1, updated_at = NOW() WHERE id = %s",
                    (existing["id"],)
                )
                conn.commit()
                return (
                    f"Vacation on {vacation_date} has been re-activated. "
                    "Milk delivery will be skipped on this date."
                )

        # Insert a new vacation record
        cursor.execute(
            """
            INSERT INTO sp_customer_vacations
                (customer_name, customer_id, vacation_date, marked_by, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 1, NOW(), NOW())
            """,
            (customer_name, user_id, vacation_date, user_id)
        )
        conn.commit()
        return (
            f"Vacation successfully marked for {vacation_date}. "
            "Milk delivery will be skipped on this date."
        )

    except Exception as e:
        return f"Error marking vacation for {vacation_date}: {e}"
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Tool 6: cancel_vacation_date
# ---------------------------------------------------------------------------

@tool
def cancel_vacation_date(user_id: int, vacation_date: str) -> str:
    """Cancel/remove a vacation day — milk delivery will resume on this date.

    vacation_date must be in YYYY-MM-DD format (e.g., '2026-03-10').

    Returns a success or error message.

    Use this to answer:
    - 'Cancel vacation on 10th March'
    - 'I changed my plans, I'll be home on 2026-03-05'
    - 'Remove vacation for 15th'
    """
    try:
        datetime.strptime(vacation_date, "%Y-%m-%d")
    except ValueError:
        return (
            f"Invalid date format '{vacation_date}'. "
            "Please provide the date in YYYY-MM-DD format (e.g., '2026-03-10')."
        )

    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, status FROM sp_customer_vacations "
            "WHERE customer_id = %s AND vacation_date = %s",
            (user_id, vacation_date)
        )
        existing = cursor.fetchone()

        if not existing:
            return f"No vacation found on {vacation_date} for your account."

        if existing["status"] == 0:
            return f"Vacation on {vacation_date} is already cancelled. No changes made."

        cursor.execute(
            "UPDATE sp_customer_vacations SET status = 0, updated_at = NOW() WHERE id = %s",
            (existing["id"],)
        )
        conn.commit()
        return (
            f"Vacation on {vacation_date} has been cancelled. "
            "Your milk delivery will resume on this date."
        )

    except Exception as e:
        return f"Error cancelling vacation for {vacation_date}: {e}"
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Exported list for agent registration
# ---------------------------------------------------------------------------

ALL_SUBSCRIPTION_TOOLS = [
    check_active_subscriptions,
    check_subscription_logs,
    get_vacation_dates,
    get_upcoming_vacations,
    add_vacation_date,
    cancel_vacation_date,
]

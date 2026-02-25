"""
order_tools.py  —  Simplified & Powerful
==========================================
8 tools total:

  1. get_orders_filtered       ← MAIN TOOL — handles 95% of all list queries
  2. get_order_details         ← single order full detail
  3. get_order_items           ← line items inside one order
  4. get_outstanding_amount    ← user's outstanding / wallet / credit limit
  5. get_subscription_orders   ← subscription plan management
  6. get_cancelled_order_reason← why/who/when cancelled
  7. get_daily_sales_summary   ← admin: today's sales dashboard
  8. get_top_report            ← admin: top customers / products / towns

Role resolution:
  user_type = 1  →  admin   (full access)
  user_type = 4  →  customer (own data only)

STATUS CODES: 3=Approved | 4=Delivered | 5=Cancelled | 6=Failed
"""

from langchain_core.tools import tool
from core.db import get_db_connection, get_user_role
from typing import Optional
from datetime import date


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _serialize(rows):
    if isinstance(rows, list):
        for row in rows:
            for k, v in row.items():
                if v is not None and not isinstance(v, (int, float, str, bool)):
                    row[k] = str(v)
    return rows


def _run_query(query: str, params: tuple):
    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return _serialize(rows)
    except Exception as e:
        return f"Query error: {e}"
    finally:
        cursor.close()
        conn.close()


def _resolve(session_user_id: int, target_user_id: Optional[int] = None):
    """
    Resolve role from DB and return (role, effective_uid).
    Admin  → can target any user (or None = all users)
    Customer → always own data only
    """
    role = get_user_role(session_user_id)
    if role == "admin":
        return role, target_user_id
    return role, session_user_id


# ===========================================================================
# 1. UNIVERSAL MULTI-FILTER ORDER LIST  ★ USE THIS FOR ALL LIST QUERIES ★
# ===========================================================================

@tool
def get_orders_filtered(
    session_user_id: int,

    # ── Status ──────────────────────────────────────────────────────────────
    status_code: Optional[int] = None,
    # 3=Approved | 4=Delivered | 5=Cancelled | 6=Failed

    # ── Date ────────────────────────────────────────────────────────────────
    use_today: bool = False,          # True → DATE(order_date) = CURDATE()
    order_date: Optional[str] = None, # exact date YYYY-MM-DD
    start_date: Optional[str] = None, # range start YYYY-MM-DD
    end_date:   Optional[str] = None, # range end   YYYY-MM-DD

    # ── Location (admin only) ────────────────────────────────────────────────
    town_name:          Optional[str] = None,
    town_id:            Optional[int] = None,
    route_id:           Optional[int] = None,
    route_name:         Optional[str] = None,
    locality_name:      Optional[str] = None,
    hub_id:             Optional[int] = None,
    production_unit_id: Optional[int] = None,
    distributor_type:   Optional[str] = None,

    # ── User ────────────────────────────────────────────────────────────────
    target_user_id: Optional[int] = None,

    # ── Misc filters ────────────────────────────────────────────────────────
    is_subscribed:  Optional[bool]  = None,
    is_return:      Optional[bool]  = None,
    is_free_order:  Optional[bool]  = None,
    min_amount:     Optional[float] = None,
    order_code:     Optional[str]   = None,

    limit: int = 100,
):
    """
    ★ PRIMARY ORDER QUERY TOOL ★

    Combine ANY filters in one call. Use this for ALL order list questions:
      • "Show approved orders today in Chandigarh"
          → status_code=3, use_today=True, town_name='Chandigarh'
      • "Show my last 10 orders"
          → limit=10
      • "Delivered orders between 1 Feb and 10 Feb"
          → status_code=4, start_date='2026-02-01', end_date='2026-02-10'
      • "Cancelled subscription orders this month"
          → status_code=5, is_subscribed=True, start_date=..., end_date=...
      • "Show orders from route 5 with amount > 5000"
          → route_id=5, min_amount=5000
      • "Show all orders of user 1001" (admin)
          → target_user_id=1001
      • "Show return orders from Mohali" (admin)
          → is_return=True, town_name='Mohali'

    Location filters (town, route, hub, locality, production_unit, distributor_type)
    require admin access; they are silently ignored for customers.
    Customers are always scoped to their own orders regardless of target_user_id.
    """
    role, uid = _resolve(session_user_id, target_user_id)

    conditions: list = []
    params:     list = []

    # ── user scope ────────────────────
    if uid:
        conditions.append("user_id = %s")
        params.append(uid)

    # ── status ────────────────────────
    if status_code is not None:
        conditions.append("order_status = %s")
        params.append(status_code)

    # ── date ──────────────────────────
    if use_today:
        conditions.append("DATE(order_date) = CURDATE()")
    elif order_date:
        conditions.append("DATE(order_date) = %s")
        params.append(order_date)
    elif start_date and end_date:
        conditions.append("DATE(order_date) BETWEEN %s AND %s")
        params += [start_date, end_date]
    elif start_date:
        conditions.append("DATE(order_date) >= %s")
        params.append(start_date)
    elif end_date:
        conditions.append("DATE(order_date) <= %s")
        params.append(end_date)

    # ── order code ────────────────────
    if order_code:
        conditions.append("order_code = %s")
        params.append(order_code)

    # ── location (admin only) ─────────
    if role == "admin":
        if town_id:
            conditions.append("town_id = %s"); params.append(town_id)
        elif town_name:
            conditions.append("town_name LIKE %s"); params.append(f"%{town_name}%")

        if route_id:
            conditions.append("route_id = %s"); params.append(route_id)
        elif route_name:
            conditions.append("route_name LIKE %s"); params.append(f"%{route_name}%")

        if locality_name:
            conditions.append("locality_name LIKE %s"); params.append(f"%{locality_name}%")

        if hub_id:
            conditions.append("hub_id = %s"); params.append(hub_id)

        if production_unit_id:
            conditions.append("production_unit_id = %s"); params.append(production_unit_id)

        if distributor_type:
            conditions.append("distributor_type LIKE %s"); params.append(f"%{distributor_type}%")

    # ── misc flags ────────────────────
    if is_subscribed is not None:
        conditions.append("is_subscribed = %s"); params.append(1 if is_subscribed else 0)

    if is_return is not None:
        conditions.append("is_return = %s"); params.append(1 if is_return else 0)

    if is_free_order is not None:
        conditions.append("is_free_order = %s"); params.append(1 if is_free_order else 0)

    if min_amount is not None:
        conditions.append("order_total_amount >= %s"); params.append(min_amount)

    where  = " AND ".join(conditions) if conditions else "1=1"
    params.append(limit)

    query = f"""
        SELECT id AS order_id, order_code, user_name, order_date, order_status,
               order_total_amount, town_name, route_name, locality_name,
               expected_delivery_date, delivered_date, cancelled_date,
               is_subscribed, remark, reason
        FROM sp_secondary_orders
        WHERE {where}
        ORDER BY id DESC
        LIMIT %s
    """
    rows = _run_query(query, tuple(params))
    return rows if rows else "No orders found matching the given filters."


# ===========================================================================
# 2. SINGLE ORDER DETAIL
# ===========================================================================

@tool
def get_order_details(
    session_user_id: int,
    order_id: Optional[int] = None,
    order_code: Optional[str] = None,
):
    """
    Get full details of ONE specific order by order_id OR order_code.
    Customers can only view their own orders.
    """
    role, _ = _resolve(session_user_id)
    if not order_id and not order_code:
        return "Please provide order_id or order_code."

    conds, params = [], []
    if order_id:
        conds.append("id = %s"); params.append(order_id)
    if order_code:
        conds.append("order_code = %s"); params.append(order_code)

    where = " OR ".join(conds)
    if role == "customer":
        where = f"({where}) AND user_id = %s"
        params.append(session_user_id)

    rows = _run_query(f"SELECT * FROM sp_secondary_orders WHERE {where}", tuple(params))
    return rows if rows else "Order not found."


# ===========================================================================
# 3. ORDER LINE ITEMS
# ===========================================================================

@tool
def get_order_items(
    session_user_id: int,
    order_id: Optional[int] = None,
    order_code: Optional[str] = None,
):
    """
    Get all products/items inside a specific order.
    Customers can only view their own orders.
    """
    role, _ = _resolve(session_user_id)
    if not order_id and not order_code:
        return "Please provide order_id or order_code."

    if order_id:
        base, params = "o.id = %s", [order_id]
    else:
        base, params = "o.order_code = %s", [order_code]

    if role == "customer":
        base += " AND o.user_id = %s"; params.append(session_user_id)

    query = f"""
        SELECT d.product_name, d.product_variant_name, d.quantity, d.rate,
               d.amount, d.gst, d.taxable_amount, d.final_amount,
               d.quantity_in_ltr, d.quantity_in_pouch, d.is_free,
               d.milk_offer_id, d.special_offer_id, d.coins
        FROM sp_secondary_orders o
        LEFT JOIN sp_secondary_order_details d ON o.id = d.order_id
        WHERE {base}
    """
    rows = _run_query(query, tuple(params))
    return rows if rows else "No items found for this order."


# ===========================================================================
# 4. USER FINANCIAL INFO
# ===========================================================================

@tool
def get_outstanding_amount(
    session_user_id: int,
    target_user_id: Optional[int] = None,
):
    """
    Get outstanding amount, wallet balance, and credit limit for a user.
    Customers can only check their own. Admins can check any user.
    """
    role, uid = _resolve(session_user_id, target_user_id)
    lookup_id = uid or session_user_id

    query = """
        SELECT u.id, CONCAT(u.first_name,' ',u.last_name) AS customer_name,
               b.outstanding_amount, b.wallet_amount, b.credit_limit
        FROM sp_users u
        LEFT JOIN sp_basic_details b ON u.id = b.user_id
        WHERE u.id = %s
    """
    rows = _run_query(query, (lookup_id,))
    return rows if rows else f"No financial info found for user_id={lookup_id}."


# ===========================================================================
# 5. SUBSCRIPTION MANAGEMENT
# ===========================================================================

@tool
def get_subscription_orders(
    session_user_id: int,
    target_user_id: Optional[int] = None,
    plan_type: Optional[str] = None,   # 'daily','alternate_day','double_alternate','custom'
    status: Optional[str] = None,      # 'active','cancelled', etc.
    subscription_id: Optional[int] = None,
):
    """
    Get subscription plans from sp_subscriptions.
    Use this for subscription management queries — NOT for delivered/failed subscription orders
    (use get_orders_filtered with is_subscribed=True for those).
    Customers see only their own subscriptions.
    """
    role, uid = _resolve(session_user_id, target_user_id)

    conds, params = [], []
    if uid:
        conds.append("user_id = %s"); params.append(uid)
    if plan_type:
        conds.append("plan_type = %s"); params.append(plan_type)
    if status:
        conds.append("status = %s"); params.append(status)
    if subscription_id:
        conds.append("id = %s"); params.append(subscription_id)

    where = " AND ".join(conds) if conds else "1=1"
    query = f"""
        SELECT id, user_name, product_name, product_variant_name, plan_type,
               plan_days, quantity, rate, total_amount, start_date, end_date,
               status, delivery_instruction, custom_days
        FROM sp_subscriptions WHERE {where} ORDER BY id DESC
    """
    rows = _run_query(query, tuple(params))
    return rows if rows else "No subscriptions found."


# ===========================================================================
# 6. CANCELLATION REASON
# ===========================================================================

@tool
def get_cancelled_order_reason(
    session_user_id: int,
    order_id: Optional[int] = None,
    order_code: Optional[str] = None,
):
    """
    Find out why a specific order was cancelled, who cancelled it, and when.
    Customers can only check their own orders.
    """
    role, _ = _resolve(session_user_id)
    if not order_id and not order_code:
        return "Please provide order_id or order_code."

    if order_id:
        base, params = "id = %s", [order_id]
    else:
        base, params = "order_code = %s", [order_code]

    if role == "customer":
        base += " AND user_id = %s"; params.append(session_user_id)

    query = f"""
        SELECT id, order_code, order_status, reason, remark,
               cancelled_by, cancelled_date, updated_by, updated_date
        FROM sp_secondary_orders WHERE ({base}) AND order_status = 5
    """
    rows = _run_query(query, tuple(params))
    return rows if rows else "Order not found or is not cancelled."


# ===========================================================================
# 7. DAILY SALES SUMMARY  [ADMIN ONLY]
# ===========================================================================

@tool
def get_daily_sales_summary(
    session_user_id: int,
    summary_date: Optional[str] = None,   # YYYY-MM-DD, defaults to today
):
    """
    [ADMIN ONLY] Complete daily sales dashboard:
    total orders, delivered, cancelled, failed, gross revenue, delivered revenue.
    Also returns product-wise breakdown for the day.
    Defaults to today unless summary_date is provided.
    """
    role, _ = _resolve(session_user_id)
    if role != "admin":
        return "Access denied: daily sales summary requires admin access (user_type=1)."

    d = summary_date or str(date.today())

    order_summary = _run_query("""
        SELECT
            COUNT(*) AS total_orders,
            SUM(CASE WHEN order_status = 3 THEN 1 ELSE 0 END) AS approved,
            SUM(CASE WHEN order_status = 4 THEN 1 ELSE 0 END) AS delivered,
            SUM(CASE WHEN order_status = 5 THEN 1 ELSE 0 END) AS cancelled,
            SUM(CASE WHEN order_status = 6 THEN 1 ELSE 0 END) AS failed,
            SUM(order_total_amount) AS gross_revenue,
            SUM(CASE WHEN order_status=4 THEN order_total_amount ELSE 0 END) AS delivered_revenue,
            SUM(CASE WHEN order_status=5 THEN order_total_amount ELSE 0 END) AS cancelled_revenue
        FROM sp_secondary_orders
        WHERE DATE(order_date) = %s
    """, (d,))

    product_summary = _run_query("""
        SELECT d.product_name, d.product_variant_name,
               SUM(d.quantity) AS total_qty,
               SUM(d.quantity_in_ltr) AS total_liters,
               SUM(d.quantity_in_pouch) AS total_pouches,
               SUM(d.amount) AS total_amount,
               SUM(CASE WHEN d.is_free=1 THEN d.quantity ELSE 0 END) AS free_qty
        FROM sp_secondary_order_details d
        JOIN sp_secondary_orders o ON o.id = d.order_id
        WHERE DATE(o.order_date) = %s
        GROUP BY d.product_name, d.product_variant_name
        ORDER BY total_amount DESC
    """, (d,))

    return {
        "date": d,
        "order_summary": order_summary,
        "product_breakdown": product_summary,
    }


# ===========================================================================
# 8. TOP REPORT  [ADMIN ONLY]
# ===========================================================================

@tool
def get_top_report(
    session_user_id: int,
    report_type: str,        # 'customers' | 'products' | 'towns'
    limit: int = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """
    [ADMIN ONLY] Generate a top-N leaderboard report.
    report_type options:
      - 'customers' → top customers by revenue
      - 'products'  → top products by quantity sold
      - 'towns'     → top towns by revenue

    Optionally filter by start_date / end_date (YYYY-MM-DD).
    Only counts delivered orders (status=4).
    """
    role, _ = _resolve(session_user_id)
    if role != "admin":
        return "Access denied: top reports require admin access (user_type=1)."

    date_filter = ""
    params: list = []
    if start_date and end_date:
        date_filter = "AND DATE(o.order_date) BETWEEN %s AND %s"
        params += [start_date, end_date]

    if report_type == "customers":
        query = f"""
            SELECT user_id, user_name,
                   COUNT(*) AS total_orders,
                   SUM(order_total_amount) AS total_revenue
            FROM sp_secondary_orders o
            WHERE order_status = 4 {date_filter}
            GROUP BY user_id, user_name
            ORDER BY total_revenue DESC LIMIT %s
        """
        params.append(limit)
        return _run_query(query, tuple(params))

    elif report_type == "products":
        query = f"""
            SELECT d.product_name, d.product_variant_name,
                   SUM(d.quantity) AS total_qty,
                   SUM(d.quantity_in_ltr) AS total_liters,
                   SUM(d.amount) AS total_revenue
            FROM sp_secondary_order_details d
            JOIN sp_secondary_orders o ON o.id = d.order_id
            WHERE o.order_status = 4 {date_filter}
            GROUP BY d.product_name, d.product_variant_name
            ORDER BY total_qty DESC LIMIT %s
        """
        params.append(limit)
        return _run_query(query, tuple(params))

    elif report_type == "towns":
        query = f"""
            SELECT town_name,
                   COUNT(*) AS order_count,
                   SUM(order_total_amount) AS total_revenue
            FROM sp_secondary_orders o
            WHERE order_status = 4 {date_filter}
            GROUP BY town_name
            ORDER BY total_revenue DESC LIMIT %s
        """
        params.append(limit)
        return _run_query(query, tuple(params))

    else:
        return f"Unknown report_type '{report_type}'. Use: 'customers', 'products', or 'towns'."


# ---------------------------------------------------------------------------
# ALL_ORDER_TOOLS — import this in agents/order.py
# ---------------------------------------------------------------------------

ALL_ORDER_TOOLS = [
    get_orders_filtered,       # ★ main workhorse — handles 95% of queries
    get_order_details,         # single-order full detail
    get_order_items,           # items inside an order
    get_outstanding_amount,    # user financial info
    get_subscription_orders,   # subscription plans
    get_cancelled_order_reason,# why was it cancelled
    get_daily_sales_summary,   # [admin] daily dashboard
    get_top_report,            # [admin] top customers/products/towns
]

"""
product_tools.py — Product Catalog & Offers Tools
==================================================
4 tools total:

  1. get_product_catalog      — browse all available products with pricing
  2. get_product_details      — full details & all variants for a named product
  3. get_active_offers        — milk offers (buy-X-get-Y) + special offers (free items)
  4. get_subscribable_products — products eligible for subscription plans

Tables used:
  sp_products              — product master (name, class, description, status)
  sp_product_variants      — variants with pricing (mrp, sp_customer, offer_price)
  sp_product_class         — product categories
  sp_milk_offer_master     — milk quantity offers (buy X qty → get Y free)
  sp_special_offer_master  — order-level offers (min amount → free items)
  sp_special_offer_free_items — free item details for special offers

Pricing columns in sp_product_variants:
  mrp         → Maximum Retail Price
  sp_customer → Actual customer selling price
  offer_price → Discounted price (when any_discount = 1)
"""

from langchain_core.tools import tool
from core.db import get_db_connection


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _serialize(rows, array_name="data") -> str:
    """
    Serialize DB rows into TOON (Token-Oriented Object Notation).
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
    """Convert date/datetime/Decimal objects to plain strings/floats."""
    for row in rows:
        for k, v in row.items():
            if v is not None and not isinstance(v, (int, float, str, bool)):
                row[k] = str(v)
    return rows


def _run_read(query: str, params: tuple = ()):
    """Execute a read-only query and return TOON-serialized results."""
    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        rows = _normalize_rows(rows)
        return _serialize(rows)
    except Exception as e:
        return f"Query error: {e}"
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Tool 1: get_product_catalog
# ---------------------------------------------------------------------------

@tool
def get_product_catalog(
    search_name: str = "",
    featured_only: bool = False,
) -> str:
    """Browse available products and their pricing.

    Parameters:
    - search_name   : (optional) partial product/variant name to filter
                      e.g., "milk", "toned", "paneer", "500ml"
    - featured_only : (optional) True → return only featured/highlighted products

    Returns product_name, variant_name, variant_size, unit, MRP, customer price,
    offer price, discount flag, subscription eligibility, and rapid delivery flag.

    Use this to answer:
    - 'What products do you have?'
    - 'Show product catalog'
    - 'Is toned milk available?'
    - 'Price of 500ml milk pouch?'
    - 'Show featured products'
    - 'Kya kya milta hai?'
    - 'Milk ka rate kya hai?'
    """
    conditions = [
        "pv.status = 1",
    ]
    params: list = []

    if search_name:
        conditions.append("(pv.product_name LIKE %s OR pv.variant_name LIKE %s)")
        like = f"%{search_name}%"
        params.extend([like, like])

    if featured_only:
        conditions.append("pv.is_feature_product = 1")

    where = " AND ".join(conditions)
    query = f"""
        SELECT
            pv.product_name,
            pv.variant_name,
            pv.variant_size,
            pv.variant_unit_name  AS unit,
            pv.mrp,
            pv.sp_customer        AS customer_price,
            pv.offer_price,
            pv.any_discount       AS has_discount,
            pv.is_subscribed      AS subscribable,
            pv.is_rapid_delivery  AS rapid_delivery
        FROM sp_product_variants pv
        WHERE {where}
        ORDER BY pv.product_name, pv.variant_size
    """
    result = _run_read(query, tuple(params))
    return result if result else "No products found matching your criteria."


# ---------------------------------------------------------------------------
# Tool 2: get_product_details
# ---------------------------------------------------------------------------

@tool
def get_product_details(product_name: str) -> str:
    """Get complete details for all variants of a specific product.

    product_name : name or partial name of the product
                   e.g., "Full Cream Milk", "Toned", "Paneer"

    Returns full details: variant name, size, quantity, unit, container, packaging,
    MRP, customer price, offer price, discount, GST, subscription eligibility,
    rapid delivery, and product description.

    Use this to answer:
    - 'Tell me more about Full Cream Milk'
    - 'What sizes are available for toned milk?'
    - 'What is the GST on paneer?'
    - 'Full Cream Milk ke saare variants dikhao'
    - 'Describe the 1 litre milk pouch'
    """
    query = """
        SELECT
            p.product_name,
            p.description         AS product_description,
            pv.id                 AS variant_id,
            pv.variant_name,
            pv.variant_size,
            pv.variant_quantity,
            pv.variant_unit_name  AS unit,
            pv.container_name,
            pv.packaging_type_name,
            pv.mrp,
            pv.sp_customer        AS customer_price,
            pv.offer_price,
            pv.any_discount       AS has_discount,
            pv.gst,
            pv.is_subscribed      AS subscribable,
            pv.is_rapid_delivery  AS rapid_delivery,
            pv.description        AS variant_description
        FROM sp_product_variants pv
        LEFT JOIN sp_products p ON pv.product_id = p.id
        WHERE (pv.product_name LIKE %s OR p.product_name LIKE %s)
          AND pv.status = 1
        ORDER BY pv.variant_size
    """
    like = f"%{product_name}%"
    result = _run_read(query, (like, like))
    return result if result else f"No product found matching '{product_name}'."


# ---------------------------------------------------------------------------
# Tool 3: get_active_offers
# ---------------------------------------------------------------------------

@tool
def get_active_offers() -> str:
    """Fetch all currently active promotional offers — two types:

    **Milk Offers** (buy-quantity-get-free):
      - Buy between min_qty and max_qty of a milk class → get offer_quantity free

    **Special Offers** (min-order-amount → free items):
      - Place an order above min_order_amount → get specific free products

    Use this to answer:
    - 'Are there any offers?'
    - 'What promotions are running?'
    - 'Free milk offer kya hai?'
    - 'Koi discount chal raha hai?'
    - 'What do I get free if I order more?'
    """
    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        # --- Milk offers ---
        cursor.execute("""
            SELECT
                'Milk Offer'          AS offer_type,
                mom.description,
                mom.min_qty,
                mom.max_qty,
                pv.product_name       AS free_product,
                pv.variant_name       AS free_variant,
                mom.offer_quantity    AS free_qty,
                mom.valid_from,
                mom.valid_to
            FROM sp_milk_offer_master mom
            LEFT JOIN sp_product_variants pv ON mom.offer_variant_id = pv.id
            WHERE mom.is_active = 1
        """)
        milk_rows = cursor.fetchall()

        # --- Special offers ---
        cursor.execute("""
            SELECT
                'Special Offer'       AS offer_type,
                CONCAT('Min order ₹', som.min_order_amount) AS description,
                pv.product_name       AS free_product,
                pv.variant_name       AS free_variant,
                sofi.free_quantity    AS free_qty,
                som.valid_from,
                som.valid_to
            FROM sp_special_offer_master som
            JOIN sp_special_offer_free_items sofi ON som.id = sofi.offer_id
            JOIN sp_product_variants pv           ON sofi.free_variant_id = pv.id
            WHERE som.is_active = 1
        """)
        special_rows = cursor.fetchall()

        all_rows = _normalize_rows(milk_rows + special_rows)

        if not all_rows:
            return "No active offers at the moment."

        return _serialize(all_rows, "offers")

    except Exception as e:
        return f"Error fetching offers: {e}"
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Tool 4: get_subscribable_products
# ---------------------------------------------------------------------------

@tool
def get_subscribable_products() -> str:
    """Fetch all products that can be added to a subscription plan.

    Returns products where is_subscribed=1 — these can be ordered on a
    daily, alternate-day, or custom recurring schedule.

    Use this to answer:
    - 'Which products can I subscribe to?'
    - 'Show subscription-eligible products'
    - 'Can I get paneer on subscription?'
    - 'Konse products daily delivery ke liye available hain?'
    - 'Subscription mein kya kya le sakte hain?'
    """
    query = """
        SELECT
            pv.product_name,
            pv.variant_name,
            pv.variant_size,
            pv.variant_unit_name  AS unit,
            pv.sp_customer        AS rate,
            pv.mrp,
            pv.description
        FROM sp_product_variants pv
        WHERE pv.is_subscribed = 1
          AND pv.status = 1
        ORDER BY pv.product_name, pv.variant_size
    """
    result = _run_read(query, ())
    return result if result else "No subscribable products found."


# ---------------------------------------------------------------------------
# Exported list for agent registration
# ---------------------------------------------------------------------------

ALL_PRODUCT_TOOLS = [
    get_product_catalog,
    get_product_details,
    get_active_offers,
    get_subscribable_products,
]

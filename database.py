
import sqlite3
import pandas as pd

DATABASE_NAME = "business_orders.db"


def initialize_database():
    """Create the SQLite database and orders table."""
    with sqlite3.connect(DATABASE_NAME) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT,
                customer TEXT,
                order_date TEXT,
                expected_delivery_date TEXT,
                status TEXT,
                order_value REAL
            )
        """)


def save_orders(orders):
    """Save uploaded orders while preserving their columns."""
    if orders.empty:
        raise ValueError("The uploaded dataset contains no orders.")

    clean_orders = orders.copy()

    # Remove an exported DataFrame index if one is present.
    if "index" in clean_orders.columns:
        clean_orders = clean_orders.drop(columns=["index"])

    required_columns = [
        "order_id",
        "customer",
        "order_date",
        "expected_delivery_date",
        "status",
        "order_value"
    ]

    missing = [
        column for column in required_columns
        if column not in clean_orders.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(missing)}"
        )

    # Store all columns, not only the required columns.
    with sqlite3.connect(DATABASE_NAME) as connection:
        clean_orders.to_sql(
            "orders",
            connection,
            if_exists="replace",
            index=False
        )


def load_orders():
    """Retrieve all saved orders using SQL."""
    with sqlite3.connect(DATABASE_NAME) as connection:
        return pd.read_sql_query(
            "SELECT * FROM orders",
            connection
        )


def get_order_count():
    """Count saved orders using SQL."""
    with sqlite3.connect(DATABASE_NAME) as connection:
        result = connection.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()
    return result[0]


def get_overdue_orders():
    """Retrieve overdue orders directly using SQL."""
    with sqlite3.connect(DATABASE_NAME) as connection:
        query = """
            SELECT *
            FROM orders
            WHERE LOWER(status) NOT IN ('delivered', 'cancelled')
              AND date(expected_delivery_date) < date('now')
            ORDER BY date(expected_delivery_date) ASC
        """
        return pd.read_sql_query(query, connection)

def get_order_value_by_status():
    """Calculate total order value for each status using SQL."""
    with sqlite3.connect(DATABASE_NAME) as connection:
        query = """
            SELECT
                status,
                COUNT(*) AS order_count,
                ROUND(SUM(order_value), 2) AS total_order_value
            FROM orders
            GROUP BY status
            ORDER BY total_order_value DESC
        """
        return pd.read_sql_query(query, connection)

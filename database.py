
import sqlite3
import pandas as pd

DATABASE_NAME = "business_orders.db"


def initialize_database():
    """Create the SQLite database if it does not exist."""
    with sqlite3.connect(DATABASE_NAME) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT,
                customer TEXT,
                expected_delivery_date TEXT,
                status TEXT,
                order_value REAL
            )
        """)


def save_orders(orders):
    """Save uploaded business orders to SQLite."""
    required_columns = [
        "order_id",
        "customer",
        "expected_delivery_date",
        "status",
        "order_value"
    ]

    missing = [
        column for column in required_columns
        if column not in orders.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(missing)}"
        )

    # Store the uploaded records in the database.
    with sqlite3.connect(DATABASE_NAME) as connection:
        orders.to_sql(
            "orders",
            connection,
            if_exists="replace",
            index=False
        )


def load_orders():
    """Retrieve saved business orders using SQL."""
    with sqlite3.connect(DATABASE_NAME) as connection:
        return pd.read_sql_query(
            "SELECT * FROM orders",
            connection
        )


def get_order_count():
    """Count saved orders using an SQL query."""
    with sqlite3.connect(DATABASE_NAME) as connection:
        result = connection.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()

    return result[0]

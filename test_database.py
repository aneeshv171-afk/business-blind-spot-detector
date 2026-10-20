
from database import initialize_database, load_orders, get_order_count

initialize_database()

orders = load_orders()

print("Orders counted by SQL:", get_order_count())
print("Orders retrieved from SQLite:", len(orders))
print("Database columns:", list(orders.columns))
print(orders.head())

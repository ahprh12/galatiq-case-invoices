import sqlite3
import os

def initialize_database(db_path: str = os.path.join("data", "inventory.db")):
    """Creates and seeds the AP Receiving Log database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Table represents what the warehouse actually received (Unbilled Receipts)
        cursor.execute("CREATE TABLE receiving_log (item TEXT PRIMARY KEY, received_qty INTEGER)")

        # Seed data matching physical goods received
        seed_data = [
            ("WidgetA", 10),  # We received exactly 10 WidgetAs
            ("WidgetB", 5),   # We received exactly 5 WidgetBs
            ("GadgetX", 5),   # We received 5 (but Invoice 1002 bills for 20)
            ("FakeItem", 0)   # Fraud check
        ]
        cursor.executemany("INSERT INTO receiving_log VALUES (?, ?)", seed_data)
        conn.commit()

    print(f"✅ Receiving log initialized at '{db_path}' with {len(seed_data)} delivery records.")

if __name__ == "__main__":
    initialize_database()
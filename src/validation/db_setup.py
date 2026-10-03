import sqlite3
import os

def initialize_database(db_path: str = os.path.join("data", "inventory.db")):
    """Creates and seeds the AP Receiving Log and Audit database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Table 1: Unbilled Receipts (Existing)
        cursor.execute("CREATE TABLE receiving_log (item TEXT PRIMARY KEY, received_qty INTEGER)")
        
        # Table 2: Deduplication Ledger (NEW)
        cursor.execute("CREATE TABLE processed_invoices (invoice_id TEXT PRIMARY KEY, processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")

        # Seed data matching physical goods received
        seed_data = [
            ("WidgetA", 10),
            ("WidgetB", 5),
            ("GadgetX", 5),
            ("FakeItem", 0)
        ]
        cursor.executemany("INSERT INTO receiving_log VALUES (?, ?)", seed_data)
        
        # Seed a duplicate invoice ID so your pytest cases pass
        cursor.execute("INSERT INTO processed_invoices (invoice_id) VALUES (?)", ("INV-DUPLICATE",))
        
        conn.commit()

    print(f"✅ Database initialized at '{db_path}' with receiving and audit tables.")

if __name__ == "__main__":
    initialize_database()
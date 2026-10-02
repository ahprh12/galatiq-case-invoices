import sqlite3
import os

def initialize_database(db_path: str = os.path.join("data", "inventory.db")):
    """Creates and seeds the SQLite mock inventory database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE inventory (item TEXT PRIMARY KEY, stock INTEGER)")

        seed_data = [
            ("WidgetA", 15),
            ("WidgetB", 10),
            ("GadgetX", 5),
            ("FakeItem", 0)
        ]
        cursor.executemany("INSERT INTO inventory VALUES (?, ?)", seed_data)
        conn.commit()

    print(f"✅ Database initialized at '{db_path}' with {len(seed_data)} seed records.")

if __name__ == "__main__":
    initialize_database()
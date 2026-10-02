import sqlite3
import pytest
from src.models import InvoiceData, LineItem
from src.validation.validator import APReconciliationValidator

@pytest.fixture
def test_db_path(tmp_path):
    """Creates a temporary, isolated SQLite database for testing."""
    db_file = tmp_path / "test_receiving.db"
    db_path = str(db_file)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE receiving_log (item TEXT PRIMARY KEY, received_qty INTEGER)")
        cursor.execute("CREATE TABLE processed_invoices (invoice_id TEXT PRIMARY KEY, processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        
        cursor.executemany("INSERT INTO receiving_log VALUES (?, ?)", [
            ("WidgetA", 10),
            ("WidgetB", 5)
        ])
        # Seed a duplicate invoice ID for the new test case
        cursor.execute("INSERT INTO processed_invoices (invoice_id) VALUES (?)", ("INV-DUPLICATE",))
        conn.commit()
        
    return db_path

def test_valid_three_way_match(test_db_path):
    validator = APReconciliationValidator(db_path=test_db_path)
    invoice = InvoiceData(
        invoice_id="INV-001", vendor="Acme", amount=100.0, due_date="2026-01-01",
        items=[LineItem(item="WidgetA", quantity=10)]
    )
    
    report = validator.validate(invoice)
    assert report.is_valid is True
    assert report.is_duplicate is False
    assert report.item_reports[0].status == "PASS"

def test_overbilled_discrepancy(test_db_path):
    validator = APReconciliationValidator(db_path=test_db_path)
    invoice = InvoiceData(
        invoice_id="INV-002", vendor="Acme", amount=100.0, due_date="2026-01-01",
        items=[LineItem(item="WidgetB", quantity=6)]  # Only 5 received
    )
    
    report = validator.validate(invoice)
    assert report.is_valid is False
    assert report.item_reports[0].status == "OVERBILLED"

def test_not_received_discrepancy(test_db_path):
    validator = APReconciliationValidator(db_path=test_db_path)
    invoice = InvoiceData(
        invoice_id="INV-003", vendor="Acme", amount=100.0, due_date="2026-01-01",
        items=[LineItem(item="GhostItem", quantity=1)]
    )
    
    report = validator.validate(invoice)
    assert report.is_valid is False
    assert report.item_reports[0].status == "NOT_RECEIVED"

def test_negative_quantity_invalid_data(test_db_path):
    validator = APReconciliationValidator(db_path=test_db_path)
    invoice = InvoiceData(
        invoice_id="INV-004", vendor="Acme", amount=100.0, due_date="2026-01-01",
        items=[LineItem(item="WidgetA", quantity=-5)]
    )
    
    report = validator.validate(invoice)
    assert report.is_valid is False
    assert report.item_reports[0].status == "INVALID_DATA"

def test_duplicate_invoice_rejection(test_db_path):
    validator = APReconciliationValidator(db_path=test_db_path)
    invoice = InvoiceData(
        invoice_id="INV-DUPLICATE", vendor="Acme", amount=100.0, due_date="2026-01-01",
        items=[LineItem(item="WidgetA", quantity=5)]
    )
    
    report = validator.validate(invoice)
    assert report.is_valid is False
    assert report.is_duplicate is True
    assert report.item_reports[0].status == "DUPLICATE"
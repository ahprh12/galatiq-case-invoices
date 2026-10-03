import sqlite3
import os
from datetime import datetime
from src.models import InvoiceData

class AuditLedger:
    def __init__(self, db_path: str = os.path.join("data", "inventory.db"), log_path: str = os.path.join("data", "audit_rejections.log")):
        self.db_path = db_path
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log_hold_or_rejection(self, invoice: InvoiceData, status: str, reasons: str, notes: str):
        """Logs rejected or escalated invoices to a plain text audit file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            f"[{timestamp}] STATUS: {status} | ID: {invoice.invoice_id} | "
            f"VENDOR: {invoice.vendor} | AMOUNT: ${invoice.amount:,.2f}\n"
            f"    -> REASONS: {reasons}\n"
            f"    -> NOTES: {notes}\n"
            f"{'-'*80}\n"
        )
        with open(self.log_path, "a") as f:
            f.write(entry)

    def process_approved_payment(self, invoice: InvoiceData):
        """Executes the atomic DB transaction for approved payments to close the loop."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 1. Record the invoice in the audit table to prevent future duplicates
            cursor.execute(
                "INSERT INTO processed_invoices (invoice_id) VALUES (?)", 
                (invoice.invoice_id,)
            )
            
            # 2. Deduct billed items from the receiving_log
            for line in invoice.items:
                cursor.execute(
                    "UPDATE receiving_log SET received_qty = received_qty - ? WHERE item = ?",
                    (line.quantity, line.item)
                )
            conn.commit()
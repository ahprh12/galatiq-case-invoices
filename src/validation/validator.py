import sqlite3
import os
from typing import List, Dict
from src.models import InvoiceData, ItemValidation, ValidationReport

class APReconciliationValidator:
    def __init__(self, db_path: str = os.path.join("data", "inventory.db")):
        self.db_path = db_path

    def _is_duplicate(self, invoice_id: str) -> bool:
        """Checks the audit table to see if this invoice was already processed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_invoices WHERE invoice_id = ?", (invoice_id,))
            return cursor.fetchone() is not None

    def _fetch_receipts_bulk(self, item_names: List[str]) -> Dict[str, int]:
        """Bulk query against the receiving log to check physical deliveries."""
        if not item_names:
            return {}

        placeholders = ','.join('?' * len(item_names))
        query = f"SELECT item, received_qty FROM receiving_log WHERE item IN ({placeholders})"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, item_names)
            return {row[0]: row[1] for row in cursor.fetchall()}

    def validate(self, invoice: InvoiceData) -> ValidationReport:
        # 1. Check Deduplication Gate using the extracted ID
        is_dup = self._is_duplicate(invoice.invoice_id)
        overall_valid = not is_dup  # Automatically invalid if duplicate

        # 2. Check Line Items
        item_names = list({line.item for line in invoice.items})
        receiving_ledger = self._fetch_receipts_bulk(item_names)
        
        item_reports = []

        for line in invoice.items:
            status = "PASS"
            reason = None
            received = receiving_ledger.get(line.item)

            if is_dup:
                status, reason = "DUPLICATE", f"Invoice ID {invoice.invoice_id} already processed."
            elif line.quantity < 0:
                status, reason = "INVALID_DATA", f"Negative quantity billed ({line.quantity})."
                overall_valid = False
            elif received is None or received == 0:
                status, reason = "NOT_RECEIVED", "Item was never received at the warehouse."
                overall_valid = False
            elif line.quantity > received:
                status, reason = "OVERBILLED", f"Vendor billed for {line.quantity}, but only {received} were received."
                overall_valid = False

            item_reports.append(ItemValidation(
                item=line.item,
                billed_qty=line.quantity,
                received_qty=received,
                status=status,
                reason=reason
            ))

        return ValidationReport(
            invoice_id=invoice.invoice_id,
            is_duplicate=is_dup,
            vendor=invoice.vendor,
            amount=invoice.amount,
            is_valid=overall_valid,
            item_reports=item_reports
        )
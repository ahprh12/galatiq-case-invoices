import sqlite3
import os
from typing import List, Dict
from src.models import InvoiceData, ItemValidation, ValidationReport

class InventoryValidator:
    def __init__(self, db_path: str = os.path.join("data", "inventory.db")):
        self.db_path = db_path

    def _fetch_stock_bulk(self, item_names: List[str]) -> Dict[str, int]:
        """Bulk query to avoid N+1 query overhead."""
        if not item_names:
            return {}

        placeholders = ','.join('?' * len(item_names))
        query = f"SELECT item, stock FROM inventory WHERE item IN ({placeholders})"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, item_names)
            return {row[0]: row[1] for row in cursor.fetchall()}

    def validate(self, invoice: InvoiceData) -> ValidationReport:
        item_names = list({line.item for line in invoice.items})
        stock_ledger = self._fetch_stock_bulk(item_names)

        overall_valid = True
        item_reports = []

        for line in invoice.items:
            status = "PASS"
            reason = None
            available = stock_ledger.get(line.item)

            if line.quantity < 0:
                status, reason = "INVALID_DATA", f"Negative quantity requested ({line.quantity})."
                overall_valid = False
            elif available is None:
                status, reason = "UNKNOWN_ITEM", "Item not found in master inventory."
                overall_valid = False
            elif available == 0:
                status, reason = "OUT_OF_STOCK", "Item is completely out of stock."
                overall_valid = False
            elif line.quantity > available:
                status, reason = "INSUFFICIENT_STOCK", f"Requested {line.quantity}, but only {available} available."
                overall_valid = False

            item_reports.append(ItemValidation(
                item=line.item,
                requested=line.quantity,
                available=available,
                status=status,
                reason=reason
            ))

        return ValidationReport(
            vendor=invoice.vendor,
            amount=invoice.amount,
            is_valid=overall_valid,
            item_reports=item_reports
        )
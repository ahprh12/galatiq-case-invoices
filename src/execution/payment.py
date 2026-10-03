from src.models import InvoiceData
from src.execution.audit import AuditLedger

def mock_payment(vendor: str, amount: float) -> dict:
    """Mock banking API required by the business case."""
    print(f"    💸 [MOCK BANK API] Paid ${amount:,.2f} to {vendor}")
    return {"status": "success"}

class ExecutionAgent:
    def __init__(self):
        self.ledger = AuditLedger()

    def execute(self, invoice: InvoiceData, decision) -> bool:
        if decision.status == "APPROVED":
            # 1. Call Mock Payment API
            payment_result = mock_payment(invoice.vendor, invoice.amount)
            
            if payment_result.get("status") == "success":
                # 2. Update the Ledger (Atomic Transaction)
                self.ledger.process_approved_payment(invoice)
                print(f"    ✅ [LEDGER] Invoice '{invoice.invoice_id}' logged. Inventory depleted.")
                return True
        else:
            # 3. Log Rejection or Escalation
            reasons = decision.rejection_reasons if decision.rejection_reasons else "N/A - Escalated to VP"
            self.ledger.log_hold_or_rejection(
                invoice=invoice, 
                status=decision.status, 
                reasons=reasons,
                notes=decision.decision_notes
            )
            print(f"    🛑 [AUDIT] Invoice blocked from payment. Logged to 'data/audit_rejections.log'.")
            return False
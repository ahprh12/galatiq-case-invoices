import argparse
import sys
from src.ingestion.extractor import ExtractionAgent
from src.validation.validator import APReconciliationValidator
from src.approval.reviewer import ApprovalAgent
from src.execution.payment import ExecutionAgent # NEW: Import the Execution Agent

def run_pipeline(invoice_path: str):
    print("=" * 60)
    print(f"📄 Processing Invoice: {invoice_path}")
    print("=" * 60)

    # --- Stage 1: Extraction ---
    print("\n[Stage 1] Ingesting and Extracting...")
    extractor = ExtractionAgent()
    try:
        invoice_data = extractor.extract_invoice(invoice_path)
        print(f"  • Extracted Invoice ID: {invoice_data.invoice_id}")
        print(f"  • Extracted Vendor:     {invoice_data.vendor}")
        print(f"  • Total Amount:        ${invoice_data.amount:,.2f}")
        print(f"  • Due Date:            {invoice_data.due_date}")
        print(f"  • Items Count:         {len(invoice_data.items)}")
    except Exception as e:
        print(f"❌ Stage 1 Extraction Failed: {e}")
        sys.exit(1)

    # --- Stage 2: AP Reconciliation & Audit History ---
    print("\n[Stage 2] Reconciling against Receiving Log & Audit History...")
    validator = APReconciliationValidator()
    validation_report = validator.validate(invoice_data)

    print(f"  • Validation Status: {'VALID' if validation_report.is_valid else 'INVALID'}")
    if validation_report.is_duplicate:
        print(f"  • DUPLICATE DETECTED: Invoice ID {validation_report.invoice_id} has already been processed.")
        
    for item in validation_report.item_reports:
        mark = "✓" if item.status == "PASS" else "✗"
        reason = f" - {item.reason}" if item.reason else ""
        print(f"    [{mark}] {item.item}: Billed {item.billed_qty} / Received {item.received_qty} [{item.status}]{reason}")

    # --- Stage 3: Policy & Approval Review ---
    print("\n[Stage 3] Evaluating Policy & Critique Loop...")
    reviewer = ApprovalAgent()
    decision = reviewer.review(invoice_data, validation_report)

    status_icons = {
        "APPROVED": "✅",
        "REQUIRES_ELEVATED_APPROVAL": "⚠️",
        "REJECTED": "❌"
    }
    icon = status_icons.get(decision.status, "ℹ️")

    print(f"  • Decision:          {icon} {decision.status}")
    print(f"  • VP Review Needed:  {decision.requires_vp_review}")
    if decision.rejection_reasons:
        print(f"  • Rejection Reasons: {decision.rejection_reasons}")
    print(f"  • Executive Notes:   {decision.decision_notes}")
    
    # --- Stage 4: Execution & Payment ---
    print("\n[Stage 4] Execution & Ledger Update...")
    executor = ExecutionAgent()
    executor.execute(invoice_data, decision)
    
    print("=" * 60)
    print("🎉 Pipeline Complete.")
    print("=" * 60)

    return invoice_data, validation_report, decision

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Agent AP Invoice Ingestion & Validation Pipeline")
    parser.add_argument(
        "--invoice_path",
        type=str,
        required=True,
        help="Path to the invoice file (txt, json, csv, xml, pdf)"
    )

    args = parser.parse_args()
    run_pipeline(args.invoice_path)
Assumptions for the assignment - Aakash.

1. Domain & Accounting Assumptions
Receiving Log as "Unbilled Receipts": The database table receiving_log does not represent total historical warehouse stock or total lifetime physical inventory; it models an active "Unbilled Receipts" clearing account (goods physically delivered and verified at the warehouse that have not yet been matched to a bill).

Deterministic Dual-Thresholds: A line item passes 3-Way Match validation if and only if the billed quantity is positive and less than or equal to the unbilled quantity currently recorded in receiving_log.

Zero-Tolerance for Overbilling or Phantom Goods: Any line item where the billed quantity exceeds the received quantity (OVERBILLED) or where the item does not exist or has 0 recorded receipts (NOT_RECEIVED) automatically fails the 3-Way Match and invalidates the entire invoice.

Positive Quantity Constraint: Line items containing negative or zero quantities are treated as corrupted data (INVALID_DATA) and are rejected immediately before matching against the ledger.

2. Deduplication & Identity Assumptions
Content-Extracted Identity: The system assumes that an invoice_id can and must be extracted directly from the document payload by the LLM (with a deterministic fallback format like VENDOR-YYYYMMDD if an explicit number is absent), rather than relying on brittle file names.

Audit Table Persistence: The processed_invoices table acts as a simple, durable ledger of previously completed invoices. An incoming invoice matching an ID in this table is flagged as is_duplicate = True and rejected before downstream financial processing.

3. Pipeline & Orchestration Assumptions
Decoupled Architecture: Ingestion/Extraction (Stage 1), Ledger Reconciliation (Stage 2), Policy Approval (Stage 3), and Payment Execution (Stage 4) are strictly decoupled. Stages communicate solely through strongly typed Pydantic contracts (InvoiceData, ValidationReport, ApprovalDecision).

Deterministic Guardrails Precede LLM Critique: Business policy and math gates are hard deterministic rules (Python/SQL). An invoice that fails receiving reconciliation or deduplication cannot be approved by an LLM prompt hallucination.

Separation of Authorization and Execution: The $10,000 threshold strictly routes invoices into REQUIRES_ELEVATED_APPROVAL (flagging requires_vp_review = True), reserving automatic APPROVED status only for clean invoices under $10,000.

Isolated Testing Environment: Test suites operate on ephemeral, isolated SQLite databases (tmp_path) to ensure unit and regression tests never alter production data, with LLM calls mocked out to keep test execution fast, deterministic, and cost-free.
### Aakash's Architectural & Business Assumptions — Acme Corp AP Automation Pipeline

#### 1. Domain & Accounting Assumptions (3-Way Match)
* **Receiving Log as "Unbilled Receipts":** The database table `receiving_log` does not model total lifetime warehouse inventory; it models an active "Unbilled Receipts" clearing account (goods physically received and inspected at the dock that have not yet been settled against a vendor bill).
* **Deterministic Dual-Thresholds:** A line item passes 3-Way Match validation if and only if the billed quantity is positive and less than or equal to the unbilled quantity currently recorded in `receiving_log`.
* **Zero-Tolerance for Overbilling or Phantom Goods:** Any line item where the billed quantity exceeds the received quantity (`OVERBILLED`) or where the item does not exist or has 0 recorded receipts (`NOT_RECEIVED`) automatically fails validation and marks the entire invoice invalid.
* **Positive Quantity Constraint:** Line items containing negative or zero quantities are treated as corrupted data (`INVALID_DATA`) and are rejected immediately before matching against the ledger.

#### 2. Settlement Mutation & Deduplication Assumptions
* **Atomic State Mutation (Post-Payment Settlement):** Upon successful approval and payment execution in Stage 4, the system atomically deducts billed quantities from `receiving_log` and commits the invoice ID to `processed_invoices`.
* **Stateful Testing & DB Re-Seeding:** Because successful transactions deplete unbilled receipts to prevent double-invoicing, running multiple valid invoices in succession against the same items will deplete available receipts, therefore testing environments must utilize the UI reset control (`🔄 Reset / Re-seed Inventory DB`) or run the command `python -m src.validation.db_setup` to restore baseline stock between runs.
* **Content-Extracted Identity:** The system assumes that an `invoice_id` must be extracted directly from the document payload by the LLM (with a deterministic fallback format like `VENDOR-YYYYMMDD` if an explicit number is absent), rather than relying on file names.
* **Deduplication Gate:** An incoming invoice matching an ID in `processed_invoices` is flagged as `is_duplicate = True` (`DUPLICATE`) and immediately halted before financial settlement.

#### 3. Agentic Pipeline & Governance Assumptions
* **Decoupled Architecture:** Ingestion/Extraction (Stage 1), Ledger Reconciliation (Stage 2), Policy Approval (Stage 3), and Payment Execution (Stage 4) are strictly decoupled. Stages communicate solely through strongly typed Pydantic contracts (`InvoiceData`, `ValidationReport`, `ApprovalDecision`).
* **Native Tool-Calling Contracts:** Rather than relying on fuzzy raw-text generation, Stage 1 forces the LLM to call `submit_extracted_invoice`, and Stage 3 forces `record_approval_decision` using Pydantic JSON schemas as formal function parameters.
* **Multi-Attempt Self-Correction Loops:** If an LLM emits a schema violation or violates a hard corporate policy (e.g., attempting to auto-approve an invoice over $10,000), the deterministic wrapper captures the error and returns a corrective `role: tool` message to the model context, giving the agent up to 3 attempts to correct its output.
* **Separation of Authorization and Execution:** The $10,000 threshold strictly routes invoices into `REQUIRES_ELEVATED_APPROVAL` (flagging `requires_vp_review = True`), reserving automatic `APPROVED` status only for clean invoices under $10,000. Payments cannot be initiated autonomously by the LLM; Stage 4 payment rails are strictly deterministic Python actions triggered only on an approved decision.
* **Telemetry & Observability:** All raw prompts, tool calls, retry feedback traces, and validation outputs are appended to `data/llm_observability.jsonl` to ensure financial auditability without leaking secrets.
* **Ephemeral Test Isolation:** Test suites operate on isolated temporary SQLite databases (`tmp_path`) with mocked LLM completions to keep automated test suites deterministic, fast, and cost-free.

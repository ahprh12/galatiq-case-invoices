# Acme Corp: Accounts Payable Automated Test Scenarios

## Overview

This document outlines the business test cases used to evaluate the automated invoice processing system. The system acts as an autonomous digital Accounts Payable department by executing the following pipeline:

- **Ingestion:** Reads incoming vendor bills and invoices across multiple file formats.
- **Extraction:** Parses and transforms relevant data into structured JSON models.
- **Validation:** Cross-references data against warehouse physical receiving logs (three-way matching).
- **Policy Governance:** Enforces corporate spending limits, vendor credibility, and compliance rules.
- **Decisioning:** Determines whether to approve, reject, or route each invoice for elevated approval.

---

## Quick Reference Index

- **Scenario 1: Clean BAU**  
  *Condition:* Known vendor, verified delivery, $<\$10,000$  
  *Decision:* `APPROVED`

- **Scenario 2: Overbilling**  
  *Condition:* Billed quantity $>$ received quantity  
  *Decision:* `REJECTED / HELD` (`OVERBILLED`)

- **Scenario 3: Ghost Orders**  
  *Condition:* Unrecorded goods / suspicious vendor  
  *Decision:* `REJECTED` (`NOT_RECEIVED`)

- **Scenario 4: Unknown Products**  
  *Condition:* Line items missing from catalog / PO registers  
  *Decision:* `REJECTED`

- **Scenario 5: Corrupted Data**  
  *Condition:* Negative units, invalid data types, missing fields  
  *Decision:* `REJECTED` (`INVALID_DATA`)

- **Scenario 6: Executive Threshold**  
  *Condition:* Legitimate invoice exceeding $\$10,000$  
  *Decision:* `REQUIRES ELEVATED APPROVAL` (`requires_vp_review=True`)

- **Scenario 7: Multi-Format Parity**  
  *Condition:* Equivalent data submitted across PDF, TXT, CSV, or JSON  
  *Decision:* `CONSISTENT PROCESSING`

- **Scenario 8: Duplicate Invoices**  
  *Condition:* Re-submission of an existing `Invoice ID`  
  *Decision:* `REJECTED` (`DUPLICATE`)

- **Scenario 9: Policy Guardrails**  
  *Condition:* Agent generates a rule-breaking decision  
  *Decision:* `SELF-CORRECTION & RETRY`

---

## Detailed Test Scenarios

### 1. Standard Approved Orders (Clean BAU)

- **What happens:** A known vendor bills us for standard goods that our warehouse actually received, and the total cost is under the standard approval limit of $\$10,000$.
- **Expected System Decision:** `APPROVED` — The invoice is automatically cleared for payment.
- **Example Files Tested:**
  - `invoice_1001.txt`
  - `invoice_1004.json`
  - `invoice_1006.csv`
  - `invoice_1011.pdf`
  - `invoice_1015.csv`

### 2. Overbilling Discrepancies (Billed More Than Received)

- **What happens:** A vendor bills us for a higher quantity than the warehouse physical receiving count shows (e.g., invoice lists 10 units when only 5 were received).
- **Expected System Decision:** `REJECTED / HELD` — The system prevents overpayment by flagging the unmatched items as `OVERBILLED` and stopping the transaction.
- **Example Files Tested:**
  - `invoice_1002.txt`
  - `invoice_1007.csv`

### 3. Fraudulent & Zero-Delivery Invoices (Ghost Orders)

- **What happens:** An unknown or suspicious vendor submits an invoice for items that have never been received by the warehouse (e.g., `"GhostItem"`), often combined with unrealistic terms.
- **Expected System Decision:** `REJECTED` — The system flags the items as `NOT_RECEIVED`, detects suspicious patterns, and halts payment.
- **Example Files Tested:**
  - `invoice_1003.txt` *(Fraudster LLC)*

### 4. Unknown Products (Catalog / Purchase Order Mismatch)

- **What happens:** An invoice lists product names or items that do not exist in Acme records or warehouse receiving systems.
- **Expected System Decision:** `REJECTED` — The system identifies these as unrecorded items and refuses payment until procurement or warehouse staff verify the order.
- **Example Files Tested:**
  - `invoice_1008.txt`
  - `invoice_1016.json`

### 5. Corrupted or Invalid Data (Data Integrity Issues)

- **What happens:** An invoice arrives with corrupted or nonsensical numbers, such as negative quantities (e.g., `-5` units) or missing vendor details.
- **Expected System Decision:** `REJECTED` — The system flags the document with status `INVALID_DATA` for data integrity violations and routes it for manual correction.
- **Example Files Tested:**
  - `invoice_1009.json`

### 6. High-Dollar Executive Threshold (Spending Limit Gate)

- **What happens:** An invoice is legitimate and all goods were delivered, but the total amount exceeds the $\$10,000$ automated threshold (e.g., $\$15,000$).
- **Expected System Decision:** `REQUIRES ELEVATED APPROVAL` — The system identifies that standard limits are exceeded and flags the invoice with `requires_vp_review=True` for Vice President (VP) review before funds can be released.
- **Example Files Tested:**
  - `invoice_1005.json`
  - `invoice_1013.json`

### 7. Multi-Format Consistency (Cross-Format Parity)

- **What happens:** The exact same invoice information is sent across different file types (e.g., PDF documents vs. plain text files).
- **Expected System Decision:** `CONSISTENT PROCESSING` — The system extracts identical financial data and arrives at the exact same approval decision regardless of whether the document is a PDF, CSV, JSON, XML, or plain text file.
- **Example Files Tested:**
  - `invoice_1011` (`.pdf` and `.txt`)
  - `invoice_1012` (`.pdf` and `.txt`)

### 8. Duplicate Invoice Prevention (Double-Billing Check)

- **What happens:** A vendor submits an invoice containing an Invoice ID that matches an entry in the processed invoice ledger.
- **Expected System Decision:** `REJECTED` — The system checks the audit database, detects the matching Invoice ID, flags the submission as a duplicate (`is_duplicate=True` / `DUPLICATE`), and automatically terminates the workflow to prevent double-paying.
- **Example Files Tested:**
  - `invoice_1001.txt` *(processed twice in succession)*

### 9. Agent Self-Correction & Policy Governance (LLM Guardrails)

- **What happens:** The autonomous review agent initially generates a decision that violates corporate governance guidelines (such as attempting to auto-approve an invoice exceeding $\$10,000$).
- **Expected System Decision:** `SELF-CORRECTION & RETRY` — The deterministic policy validator intercepts the contradiction, feeds the policy violation error back to the model loop as a tool message, and forces a compliant retry. If persistent violations occur past maximum attempts, a `RuntimeError` halts execution to safeguard finances.
- **Example Files Tested:**
  - *Simulated high-value compliance edge cases and retry-limit suites*

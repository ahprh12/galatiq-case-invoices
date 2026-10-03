======================================================================
ACME CORP: ACCOUNTS PAYABLE AUTOMATED TEST SCENARIOS
======================================================================

OVERVIEW
This doc outlines the business test cases used to evaluate the 
automated invoice processing system. 
The system acts as a digital Accounts Payable department: 
- it reads vendor bills/invoices
- extracts and transforms relevant data into structured JSON
- verifies the data against the warehouse receiving logs (ensuring we only pay for what actually arrived)
- checks spending limits
- decides whether to approve, reject, or escalate each invoice

----------------------------------------------------------------------
1. STANDARD APPROVED ORDERS (Clean BAU)
----------------------------------------------------------------------
• What happens:
  A known vendor bills us for standard goods that our warehouse 
  actually received, and the total cost is under the standard approval 
  limit of $10,000.
• Expected System Decision: 
  APPROVED. The invoice is automatically cleared for payment.
• Example Files Tested: 
  invoice_1001.txt, invoice_1004.json, invoice_1006.csv, 
  invoice_1011.pdf, invoice_1015.csv

----------------------------------------------------------------------
2. OVERBILLING DISCREPANCIES (Billed More Than Delivered / Received)
----------------------------------------------------------------------
• What happens:
  A vendor bills us for a higher quantity than the warehouse physical 
  receiving count shows (invoice lists 10 units when only 5 were received).
• Expected System Decision: 
  REJECTED / HELD. The system prevents overpayment by flagging the 
  unmatched items as "OVERBILLED" and stopping the transaction.
• Example Files Tested: 
  invoice_1002.txt, invoice_1007.csv

----------------------------------------------------------------------
3. FRAUDULENT & ZERO-DELIVERY INVOICES (Ghost Orders)
----------------------------------------------------------------------
• What happens:
  An unknown or suspicious vendor submits an invoice for items that 
  have never been received by the warehouse (e.g., "GhostItem"), 
  often combined with unrealistic terms.
• Expected System Decision: 
  REJECTED. The system flags the items as "NOT_RECEIVED," detects 
  the suspicious patterns, and does not make any payment.
• Example Files Tested: 
  invoice_1003.txt (Fraudster LLC)

----------------------------------------------------------------------
4. UNKNOWN PRODUCTS (Catalog / Purchase Order Mismatch)
----------------------------------------------------------------------
• What happens:
  An invoice lists product names or items that do not exist in Acme 
  records or warehouse receiving systems.
• Expected System Decision: 
  REJECTED. The system identifies these as unrecorded items and refuses 
  payment until procurement or warehouse staff verify the order.
• Example Files Tested: 
  invoice_1008.txt, invoice_1016.json

----------------------------------------------------------------------
5. CORRUPTED OR INVALID DATA (Data Integrity Issues)
----------------------------------------------------------------------
• What happens:
  An invoice arrives with corrupted or nonsensical numbers, such as 
  negative quantities (e.g., -5 units) or missing vendor details.
• Expected System Decision: 
  REJECTED. The system flags the document with status "INVALID_DATA" 
  for data integrity violations and routes it for manual correction.
• Example Files Tested: 
  invoice_1009.json

----------------------------------------------------------------------
6. HIGH-DOLLAR EXECUTIVE THRESHOLD (Spending Limit Gate)
----------------------------------------------------------------------
• What happens:
  An invoice is legitimate and all goods were delivered, but the total 
  amount exceeds the $10,000 automated threshold (e.g., $15,000).
• Expected System Decision: 
  REQUIRES ELEVATED APPROVAL. The system identifies that standard 
  limits are exceeded and flags the invoice with `requires_vp_review=True` 
  for Vice President (VP) review before funds can be released.
• Example Files Tested: 
  invoice_1005.json, invoice_1013.json

----------------------------------------------------------------------
7. MULTI-FORMAT CONSISTENCY (Cross-Format Parity)
----------------------------------------------------------------------
• What happens:
  The exact same invoice information is sent across different file 
  types (e.g., PDF documents vs. plain text files).
• Expected System Decision: 
  CONSISTENT PROCESSING. The system extracts identical financial data 
  and arrives at the exact same approval decision regardless of whether 
  the document is a PDF, CSV, JSON, XML, or plain text file.
• Example Files Tested: 
  invoice_1011 (.pdf and .txt), invoice_1012 (.pdf and .txt)

----------------------------------------------------------------------
8. DUPLICATE INVOICE PREVENTION (Double-Billing Check)
----------------------------------------------------------------------
• What happens:
  A vendor submits an invoice containing an Invoice ID that matches an entry 
  in the processed invoice ledger.
• Expected System Decision: 
  REJECTED. The system checks the audit database, detects the matching 
  Invoice ID, flags the submission as a duplicate (`is_duplicate=True` / `DUPLICATE`), 
  and automatically terminates the workflow to prevent double-paying.
• Example Files Tested: 
  invoice_1001.txt (processed twice in succession)

----------------------------------------------------------------------
9. AGENT SELF-CORRECTION & POLICY GOVERNANCE (LLM Guardrails)
----------------------------------------------------------------------
• What happens:
  The autonomous review agent initially generates a decision that violates 
  corporate governance guidelines (such as attempting to auto-approve an 
  invoice exceeding $10,000).
• Expected System Decision:
  SELF-CORRECTION & RETRY. The deterministic policy validator intercepts the 
  contradiction, feeds the policy violation error back to the model loop as a tool 
  message, and forces a compliant retry. If persistent violations occur past 
  maximum attempts, a `RuntimeError` halts execution to safeguard finances.
• Example Files Tested: 
  Simulated high-value compliance edge cases and retry-limit suites
======================================================================
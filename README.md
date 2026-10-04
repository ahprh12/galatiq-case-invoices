# Galatiq Acme Corp Case: Aakash's Proposal
⚠️ **NOTE:** Please read my [ASSUMPTIONS](docs/ASSUMPTIONS.md)!
## Quick Start: One-Click Local Web Dashboard

Get the interactive multi-agent dashboard running locally in four steps without manual virtual environment configuration or database seeding.

### Prerequisites
- **Python 3.10+** installed
- A **Gemini API Key** (available free from [Google AI Studio](https://aistudio.google.com/))
    - or just ask Aakash and maybe he'll share his if he's in a good mood >:D

---

### Step 1: Clone the Repository
Open your terminal and clone the repository to your local machine:
```bash
git clone https://github.com/ahprh12/galatiq-case-invoices.git
cd galatiq-case-invoices
```

### Step 2: Configure Your API Key
Create a .env file in the project root to securely store your API credentials:
```bash
cp .env.example .env
```

Open .env in any text editor and insert your key, or propose an interesting trade of rare Pogs with Aakash in exchange for his key...
```
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### Step 3: Running the System

#### Option A: One Click GUI Launcher via Terminal (Recommended)
```bash
# Give it a minute to perform the initial setup
./run_ui.sh
```
#### Option B: Run Per Assignment Instructions
```bash
# Chained one-liner set up command
python -m venv .venv && source .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && python -m src.validation.db_setup
# Run exactly as the instructions state
python main.py --invoice_path=data/invoices/invoice1.txt
```
#### Option C: Launch by Double-Clicking (Desktop GUI)
- Open your operating system's file manager (Files, Finder, or Explorer) and navigate into the project folder
- Ensure the script has execute permissions (run chmod +x run_ui.sh once if prompted)
- Double-click run_ui.sh and select Run (or Run in Terminal)
- When run_ui.sh executes, it performs all setup steps without manual intervention:
    - Virtual Environment: Detects or creates an isolated .venv environment and activates it
    - Dependencies: Automatically verifies and installs all required packages from requirements.txt
    - Database Initialization: Runs src/validation/db_setup.py to create and seed data/inventory.db if it does not already exist
    - App Launch: Starts the Streamlit dashboard and automatically opens your default web browser to http://localhost:8501.

### Using the Visual Interface
**1.)** Choose an Invoice: Pick any preloaded sample invoice from the dropdown (PDF, TXT, JSON, CSV, XML) or upload a custom invoice file.

**2.)** Execute the Pipeline: Click the "🚀 Process Invoice" button.

**3.)** Inspect Multi-Agent Execution: Watch the live status progression across Ingestion, 3-Way Match Ledger Validation, VP Critique Review, and Mock Payment Settlement.


*Enjoy. I'm always open to constructive feedback, Aakash.*

==========================================================

## Background

Acme Corp is a PE-backed manufacturing firm losing **$2M/year** on manual invoice processing. Invoices arrive via email as PDFs in messy formats with frequent errors. Staff manually extract data, validate against a legacy inventory database (inconsistent), obtain VP approval (via email chains), and process payment (via a banking API).

**Current pain points:**
- 30% error rate
- 5-day processing delays
- Frustrated stakeholders

## Objective

Build a **multi-agent system** that automates the end-to-end invoice processing workflow. The system must run as a working prototype — not just designs or slides.

## Workflow

The system should handle four stages:

1. **Ingestion** — Extract structured data from invoice documents (PDFs, text files). Fields include: Vendor, Amount, Items (with quantities), and Due Date. Expect unstructured text, typos, missing data, and potentially fraudulent entries.

2. **Validation** — Verify extracted data against a mock inventory database (SQLite). Flag mismatches such as quantity exceeding available stock or items not found in inventory.

3. **Approval** — Simulate VP-level review with rule-based decision-making (e.g., invoices over $10K require additional scrutiny). The agent should reason through approval/rejection with a reflection or critique loop.

4. **Payment** — If approved, call a mock payment function. If rejected, log the rejection with reasoning.

## Technical Requirements

- **LLM Integration**: Use xAI's Grok as the core reasoning engine (via the xAI API at https://grok.x.ai). Other models are acceptable if you don't have an API key.
- **Multi-Agent Orchestration**: Use a framework such as LangGraph, CrewAI, AutoGen, or a custom solution.
- **Agent Capabilities**: Function calling / tool use, structured outputs, and self-correction loops.
- **Runtime**: Assume no internet for external APIs — simulate everything locally.
- **Tech Stack**: Python (preferred), with libraries like `langchain`, `crewai`, `autogen`, `pdfplumber`, `PyMuPDF`, etc. Run locally — no cloud deployment.

## Provided Resources

### Mock Invoice Data

Sample invoices are provided in the `data/invoices/` directory in various formats (PDF, CSV, JSON, TXT). Use these as inputs for testing. The data intentionally includes a mix of clean entries and problematic ones — identifying and handling issues is part of the challenge.

### Mock Inventory Database (Required Setup)

Before running the system, you **must** create a local SQLite database that the validation agent will check invoices against. The sample invoices in `data/invoices/` reference specific items and quantities — your database needs to contain matching inventory records so the validation stage can flag mismatches, out-of-stock items, and unknown products.

Below is a starter schema and seed data that covers the core items referenced across the provided invoices:

```python
import sqlite3

conn = sqlite3.connect('inventory.db')  # Persist to file so all agents can access it
cursor = conn.cursor()

cursor.execute('CREATE TABLE IF NOT EXISTS inventory (item TEXT PRIMARY KEY, stock INTEGER)')
cursor.execute("""
    INSERT INTO inventory VALUES
    ('WidgetA', 15),
    ('WidgetB', 10),
    ('GadgetX', 5),
    ('FakeItem', 0)
""")
conn.commit()
```

**Why this matters:** The sample invoices are designed to test your validation logic against this database. For example:

| Scenario | Invoice | What should happen |
|---|---|---|
| Normal order within stock | INV-1001, INV-1004, INV-1006 | Items found, quantities valid — passes validation |
| Quantity exceeds stock | INV-1002 (requests 20× GadgetX, only 5 in stock) | Flagged as stock mismatch |
| Fraudulent / zero-stock item | INV-1003 (references FakeItem, 0 stock) | Flagged as out of stock or suspicious |
| Item not in database at all | INV-1008 (SuperGizmo, MegaSprocket), INV-1016 (WidgetC) | Flagged as unknown item |
| Invalid data | INV-1009 (negative quantity) | Flagged as data integrity issue |

You may extend the seed data with additional items or columns (e.g., unit price, category) to support richer validation — the above is the minimum needed to exercise the provided test invoices. If you want your system to also validate pricing or vendor information, consider adding tables for those as well.

### Mock Payment API

```python
def mock_payment(vendor, amount):
    print(f"Paid {amount} to {vendor}")
    return {"status": "success"}
```

### Grok API Setup

```python
from xai import Grok

client = Grok(api_key="your_key")
response = client.chat.completions.create(
    model="grok-3",
    messages=[{"role": "user", "content": "Reason about this..."}]
)
```

## Running the System

The system should be executable from the command line:

```bash
python main.py --invoice_path=data/invoices/invoice1.txt
```

Output should include structured logs and results.

## Evaluation Criteria

- **Functionality** — Does the system work end-to-end?
- **Code Quality** — Clean, testable, well-structured code with error handling and observability
- **Agentic Sophistication** — LLM integration, multi-agent flow, tool use, self-correction loops
- **Shipping Mindset** — Valuable MVP delivered under ambiguity; scope ruthlessly cut where needed
- **Presentation** — Clear translation of technical decisions to business impact
- **Above/Beyond** - Have you made it your own? Implemented additional features that make the solution feel great? Expanded assumptions? Added to test cases?
- **UI/UX** - Users will understand and enjoy using this system.

## Submission

Submit your solution as a link to a public GitHub repository — GitHub only (github.com).

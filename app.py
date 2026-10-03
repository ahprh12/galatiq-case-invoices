import os
import streamlit as st
from src.ingestion.extractor import ExtractionAgent
from src.validation.validator import APReconciliationValidator
from src.approval.reviewer import ApprovalAgent
from src.execution.payment import ExecutionAgent
from src.validation.db_setup import initialize_database

st.set_page_config(
    page_title="Acme Corp - AP Invoice Automation",
    page_icon="🏢",
    layout="wide"
)

st.title("🏢 Acme Corp — Accounts Payable AI Automation")
st.caption("Autonomous multi-agent invoice ingestion, 3-way match validation, VP policy governance, and settlement.")

# Sidebar controls
with st.sidebar:
    st.header("⚙️ System Controls")
    if st.button("🔄 Reset / Re-seed Inventory DB"):
        initialize_database()
        st.success("Ledger reset to clean state.")

    st.markdown("---")
    st.subheader("Select Sample Invoice")
    sample_dir = os.path.join("data", "invoices")
    sample_files = sorted(os.listdir(sample_dir)) if os.path.exists(sample_dir) else []
    selected_sample = st.selectbox("Choose a test file:", ["-- Select or Upload Custom --"] + sample_files)

# File Selection / Upload
uploaded_file = st.file_uploader("Or upload an invoice (PDF, TXT, JSON, CSV, XML):", type=["pdf", "txt", "json", "csv", "xml"])

target_path = None
if uploaded_file is not None:
    temp_dir = os.path.join("data", "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    target_path = os.path.join(temp_dir, uploaded_file.name)
    with open(target_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
elif selected_sample and selected_sample != "-- Select or Upload Custom --":
    target_path = os.path.join(sample_dir, selected_sample)

# Execution Action
if target_path and st.button("🚀 Process Invoice", type="primary"):
    col1, col2 = st.columns(2)

    # --- Stage 1: Extraction ---
    with st.status("Executing Multi-Agent AP Pipeline...", expanded=True) as status:
        st.write("🔍 **Stage 1 (Ingestion):** Extracting structured entities...")
        extractor = ExtractionAgent()
        try:
            invoice_data = extractor.extract_invoice(target_path)
            st.write(f"✓ Extracted Invoice ID: `{invoice_data.invoice_id}` | Vendor: `{invoice_data.vendor}` | Total: `${invoice_data.amount:,.2f}`")
        except Exception as e:
            st.error(f"Extraction failed: {e}")
            st.stop()

        # --- Stage 2: Validation ---
        st.write("📊 **Stage 2 (Validation):** Reconciling against receiving log (3-Way Match)...")
        validator = APReconciliationValidator()
        validation_report = validator.validate(invoice_data)
        st.write(f"✓ Reconciliation result: `{'PASS' if validation_report.is_valid else 'FAIL'}`")

        # --- Stage 3: Approval Review ---
        st.write("⚖️ **Stage 3 (Approval):** Evaluating policy limits and critique loop...")
        reviewer = ApprovalAgent()
        decision = reviewer.review(invoice_data, validation_report)
        st.write(f"✓ Review status: `{decision.status}`")

        # --- Stage 4: Execution ---
        st.write("💸 **Stage 4 (Execution):** Dispatching mock payment or audit logging...")
        executor = ExecutionAgent()
        executed = executor.execute(invoice_data, decision)

        status.update(label="Workflow Complete!", state="complete", expanded=False)

    # Display Results in Visual Dashboards
    st.subheader("📋 Pipeline Verdict & Audit Summary")
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Vendor", invoice_data.vendor)
    metric_col2.metric("Amount", f"${invoice_data.amount:,.2f}")
    metric_col3.metric("Decision", decision.status)
    metric_col4.metric("VP Review Flag", "Required" if decision.requires_vp_review else "Bypassed")

    if decision.status == "APPROVED":
        st.success("✅ **Invoice Approved & Paid via Banking API.** Warehouse receiving ledger updated.")
    elif decision.status == "REQUIRES_ELEVATED_APPROVAL":
        st.warning("⚠️ **Invoice Held for VP Review:** Amount exceeds $10,000 threshold.")
    else:
        st.error(f"❌ **Invoice Rejected:** {decision.rejection_reasons or 'Policy violation.'}")

    with st.expander("Executive Notes & Critique Rationale", expanded=True):
        st.write(decision.decision_notes)

    with st.expander("3-Way Match Line-Item Ledger Details", expanded=False):
        table_rows = []
        for item in validation_report.item_reports:
            table_rows.append({
                "Item": item.item,
                "Billed Qty": item.billed_qty,
                "Received Qty": item.received_qty,
                "Status": item.status,
                "Discrepancy Note": item.reason or "Matches Receiving Records"
            })
        st.table(table_rows)
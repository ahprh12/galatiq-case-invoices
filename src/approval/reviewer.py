import os
from openai import OpenAI
from dotenv import load_dotenv
from src.models import InvoiceData, ValidationReport, ApprovalDecision

load_dotenv()

class ApprovalAgent:
    SPENDING_THRESHOLD = 10000.00

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file, ask Aakash for details.")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.model = "gemini-3.5-flash-lite"

    def _generate_critique_notes(self, invoice: InvoiceData, validation: ValidationReport, base_status: str) -> str:
        """LLM-as-a-Judge: Generates executive decision notes and detects qualitative red flags."""
        prompt = f"""
You are an executive accounts payable auditor. Review this invoice and its 3-Way Match validation report:

Invoice Data:
- Vendor: {invoice.vendor}
- Amount: ${invoice.amount:,.2f}
- Due Date: {invoice.due_date}
- Items: {[item.model_dump() for item in invoice.items]}

Validation Report:
- Receiving Match Valid: {validation.is_valid}
- Discrepancies: {[r.model_dump() for r in validation.item_reports if r.status != 'PASS']}

Current Base Policy Status: {base_status}

Provide a concise, 1-2 sentence executive justification for the AP decision log. Highlight any qualitative red flags (e.g. impossible dates, overbilling, unknown items) if present.
"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a concise enterprise financial auditor. Be direct and precise."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()

    def review(self, invoice: InvoiceData, validation: ValidationReport) -> ApprovalDecision:
        """Enforces spending thresholds and receiving checks with a reflection loop."""
        rejection_reasons = []

        # 1. Deterministic Rule: Receiving integrity
        if not validation.is_valid:
            for rep in validation.item_reports:
                if rep.status != "PASS":
                    rejection_reasons.append(f"{rep.item}: {rep.reason}")

        # 2. Policy Threshold Gate ($10,000)
        exceeds_threshold = invoice.amount > self.SPENDING_THRESHOLD

        # Determine Baseline Status
        if rejection_reasons:
            status = "REJECTED"
        elif exceeds_threshold:
            status = "REQUIRES_ELEVATED_APPROVAL"
        else:
            status = "APPROVED"

        # 3. LLM Critique & Audit Justification Loop
        decision_notes = self._generate_critique_notes(invoice, validation, status)

        return ApprovalDecision(
            invoice_vendor=invoice.vendor,
            total_amount=invoice.amount,
            status=status,
            requires_vp_review=exceeds_threshold,
            decision_notes=decision_notes,
            rejection_reasons="; ".join(rejection_reasons) if rejection_reasons else None
        )
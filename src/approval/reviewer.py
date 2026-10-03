import os
import json
import time
from datetime import datetime
from openai import OpenAI
from pydantic import ValidationError
from dotenv import load_dotenv

from src.models import InvoiceData, ValidationReport, ApprovalDecision

load_dotenv()

class ApprovalAgent:
    def __init__(self, log_path: str = os.path.join("data", "llm_observability.jsonl")):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file, ask Aakash for details.")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.model = "gemini-3.5-flash-lite"
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def _log_observability(self, invoice_id: str, attempt: int, messages: list, raw_response: str, error: str = None):
        """Appends tool call arguments, prompts, and corrections to the JSONL ledger."""
        formatted_messages = []
        for m in messages:
            if hasattr(m, "model_dump"):
                formatted_messages.append(m.model_dump())
            elif isinstance(m, dict):
                formatted_messages.append(m)
            else:
                formatted_messages.append(str(m))

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": "ApprovalAgent",
            "invoice_id": invoice_id,
            "attempt": attempt + 1,
            "messages": formatted_messages,
            "raw_response": str(raw_response) if raw_response is not None else "",
            "error": error
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")

    def _verify_policy_compliance(self, validation_report: ValidationReport, decision: ApprovalDecision) -> str | None:
        """Deterministic policy validation to detect LLM governance contradictions."""
        # Policy Rule 1: Cannot approve invalid or duplicate invoices
        if (not validation_report.is_valid or validation_report.is_duplicate) and decision.status == "APPROVED":
            return (
                f"POLICY CONTRADICTION: Invoice is invalid (Valid={validation_report.is_valid}, "
                f"Duplicate={validation_report.is_duplicate}). You cannot mark this as 'APPROVED'. "
                f"Status must be 'REJECTED'."
            )

        # Policy Rule 2: Invoices over $10k must require elevated VP review
        if validation_report.is_valid and validation_report.amount > 10000.0:
            if decision.status == "APPROVED" or not decision.requires_vp_review:
                return (
                    f"POLICY CONTRADICTION: Amount is ${validation_report.amount:,.2f} (> $10,000 threshold). "
                    f"Standard automated approval is prohibited. Status must be 'REQUIRES_ELEVATED_APPROVAL' "
                    f"and requires_vp_review must be True."
                )

        return None

    def review(self, invoice: InvoiceData, validation: ValidationReport, max_retries: int = 3) -> ApprovalDecision:
        """Evaluates invoice and validation reports using native tool calling and policy reflection."""
        decision_tool = {
            "type": "function",
            "function": {
                "name": "record_approval_decision",
                "description": "Formally record the executive review and policy approval decision.",
                "parameters": ApprovalDecision.model_json_schema()
            }
        }

        system_prompt = (
            "You are the VP-level Accounts Payable Approval Agent. Your role is to examine the invoice "
            "and 3-way match validation report, reason through discrepancies, and execute the 'record_approval_decision' tool.\n\n"
            "MANDATORY CORPORATE POLICIES:\n"
            "1. REJECT immediately if is_valid is False or is_duplicate is True.\n"
            "2. If total_amount > $10,000.00 and validation passed, status MUST be 'REQUIRES_ELEVATED_APPROVAL' "
            "and requires_vp_review MUST be True.\n"
            "3. If validation passed and total_amount <= $10,000.00, status MUST be 'APPROVED' and requires_vp_review False.\n"
            "4. Provide professional executive critique notes justifying the decision."
        )

        user_content = (
            f"--- INVOICE PAYLOAD ---\n{invoice.model_dump_json(indent=2)}\n\n"
            f"--- VALIDATION REPORT ---\n{validation.model_dump_json(indent=2)}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        last_exception = None

        for attempt in range(max_retries):
            raw_args = None
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=[decision_tool],
                    tool_choice={"type": "function", "function": {"name": "record_approval_decision"}}
                )

                message = response.choices[0].message
                if not message.tool_calls:
                    raise ValueError("Model failed to invoke record_approval_decision tool.")

                tool_call = message.tool_calls[0]
                raw_args = tool_call.function.arguments

                # Step 1: Schema validation
                decision = ApprovalDecision.model_validate_json(raw_args)

                # Step 2: Policy Compliance Check (Self-Correction Trigger)
                compliance_violation = self._verify_policy_compliance(validation, decision)
                if compliance_violation:
                    raise ValueError(compliance_violation)

                # Passed both schema and policy checks
                self._log_observability(invoice.invoice_id, attempt, messages, raw_args, error=None)
                return decision

            except (ValidationError, ValueError) as err:
                error_msg = str(err)
                print(f"    ⚠️ [Approval] Policy/Schema check failed on attempt {attempt + 1}: {error_msg}")
                self._log_observability(invoice.invoice_id, attempt, messages, raw_args or "", error=error_msg)

                # Self-Correction Loop via Tool Message Response
                messages.append(message)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id if "tool_call" in locals() and tool_call else "call_fallback",
                    "content": f"{error_msg}\n\nPlease self-correct your assessment and call 'record_approval_decision' again."
                })
                last_exception = err

            except Exception as e:
                self._log_observability(invoice.invoice_id, attempt, messages, raw_args or "", error=str(e))
                if ("503" in str(e) or "429" in str(e)) and attempt < max_retries - 1:
                    time.sleep(2 ** (attempt + 1))
                    last_exception = e
                else:
                    raise e

        raise RuntimeError(f"Approval review failed policy constraints after {max_retries} attempts: {last_exception}")
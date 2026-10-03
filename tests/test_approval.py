import os
import json
import pytest
from unittest.mock import MagicMock, patch
from src.models import InvoiceData, LineItem, ValidationReport, ItemValidation, ApprovalDecision
from src.approval.reviewer import ApprovalAgent


@pytest.fixture
def base_invoice():
    return InvoiceData(
        invoice_id="INV-TEST-001",
        vendor="Acme Industrial",
        amount=5000.0,
        due_date="2026-02-01",
        items=[LineItem(item="WidgetA", quantity=5)]
    )


@pytest.fixture
def valid_report():
    return ValidationReport(
        invoice_id="INV-TEST-001",
        is_duplicate=False,
        vendor="Acme Industrial",
        amount=5000.0,
        is_valid=True,
        item_reports=[ItemValidation(item="WidgetA", billed_qty=5, received_qty=5, status="PASS")]
    )


def mock_completion_response(decision: ApprovalDecision):
    """Helper to return a clean mock completion object."""
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = decision.model_dump_json()
    
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.arguments = decision.model_dump_json()
    mock_message.tool_calls = [mock_tool_call]
    
    mock_response.choices = [MagicMock(message=mock_message)]
    return mock_response


@patch.object(ApprovalAgent, "_log_observability")
def test_standard_approval(mock_log, base_invoice, valid_report, tmp_path):
    """Tests standard clean invoice approval under $10k."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
        agent = ApprovalAgent(log_path=str(tmp_path / "test.jsonl"))
        
        expected_decision = ApprovalDecision(
            invoice_vendor="Acme Industrial",
            total_amount=5000.0,
            status="APPROVED",
            requires_vp_review=False,
            decision_notes="All items match receiving logs."
        )
        
        with patch.object(agent.client.chat.completions, "create", return_value=mock_completion_response(expected_decision)):
            decision = agent.review(base_invoice, valid_report)
            assert decision.status == "APPROVED"
            assert decision.requires_vp_review is False


@patch.object(ApprovalAgent, "_log_observability")
def test_vp_threshold_approval(mock_log, base_invoice, valid_report, tmp_path):
    """Tests that invoices over $10k require elevated VP review."""
    base_invoice.amount = 15000.0
    valid_report.amount = 15000.0
    
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
        agent = ApprovalAgent(log_path=str(tmp_path / "test.jsonl"))
        
        expected_decision = ApprovalDecision(
            invoice_vendor="Acme Industrial",
            total_amount=15000.0,
            status="REQUIRES_ELEVATED_APPROVAL",
            requires_vp_review=True,
            decision_notes="Exceeds $10k threshold."
        )
        
        with patch.object(agent.client.chat.completions, "create", return_value=mock_completion_response(expected_decision)):
            decision = agent.review(base_invoice, valid_report)
            assert decision.status == "REQUIRES_ELEVATED_APPROVAL"
            assert decision.requires_vp_review is True


@patch.object(ApprovalAgent, "_log_observability")
def test_rejection_routing(mock_log, base_invoice, tmp_path):
    """Tests rejection when validation report is invalid."""
    invalid_report = ValidationReport(
        invoice_id="INV-TEST-001",
        is_duplicate=False,
        vendor="Acme Industrial",
        amount=5000.0,
        is_valid=False,
        item_reports=[
            ItemValidation(item="WidgetA", billed_qty=10, received_qty=5, status="OVERBILLED", reason="Overbilled by 5.")
        ]
    )
    
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
        agent = ApprovalAgent(log_path=str(tmp_path / "test.jsonl"))
        
        expected_decision = ApprovalDecision(
            invoice_vendor="Acme Industrial",
            total_amount=5000.0,
            status="REJECTED",
            requires_vp_review=False,
            decision_notes="Billed quantity exceeds received stock.",
            rejection_reasons="Discrepancy detected in WidgetA."
        )
        
        with patch.object(agent.client.chat.completions, "create", return_value=mock_completion_response(expected_decision)):
            decision = agent.review(base_invoice, invalid_report)
            assert decision.status == "REJECTED"
            assert "Discrepancy detected in WidgetA." in decision.rejection_reasons


@patch.object(ApprovalAgent, "_log_observability")
def test_duplicate_invoice_rejection(mock_log, base_invoice, tmp_path):
    """Tests rejection when invoice is flagged as a duplicate."""
    dup_report = ValidationReport(
        invoice_id="INV-TEST-001",
        is_duplicate=True,
        vendor="Acme Industrial",
        amount=5000.0,
        is_valid=True,
        item_reports=[ItemValidation(item="WidgetA", billed_qty=5, received_qty=5, status="PASS")]
    )
    
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
        agent = ApprovalAgent(log_path=str(tmp_path / "test.jsonl"))
        
        expected_decision = ApprovalDecision(
            invoice_vendor="Acme Industrial",
            total_amount=5000.0,
            status="REJECTED",
            requires_vp_review=False,
            decision_notes="Duplicate invoice detected.",
            rejection_reasons="Invoice INV-TEST-001 is a duplicate."
        )
        
        with patch.object(agent.client.chat.completions, "create", return_value=mock_completion_response(expected_decision)):
            decision = agent.review(base_invoice, dup_report)
            assert decision.status == "REJECTED"
            assert decision.requires_vp_review is False


@patch.object(ApprovalAgent, "_log_observability")
def test_self_correction_retry(mock_log, base_invoice, valid_report, tmp_path):
    """Tests that agent successfully self-corrects when initial response violates corporate policy."""
    base_invoice.amount = 15000.0
    valid_report.amount = 15000.0
    
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
        agent = ApprovalAgent(log_path=str(tmp_path / "test.jsonl"))
        
        # Attempt 1: Violates policy by approving >$10k invoice
        invalid_decision = ApprovalDecision(
            invoice_vendor="Acme Industrial",
            total_amount=15000.0,
            status="APPROVED",
            requires_vp_review=False,
            decision_notes="Approved."
        )
        # Attempt 2: Corrects policy compliance
        valid_decision = ApprovalDecision(
            invoice_vendor="Acme Industrial",
            total_amount=15000.0,
            status="REQUIRES_ELEVATED_APPROVAL",
            requires_vp_review=True,
            decision_notes="Corrected: Exceeds $10k threshold requiring VP review."
        )
        
        with patch.object(agent.client.chat.completions, "create", side_effect=[
            mock_completion_response(invalid_decision),
            mock_completion_response(valid_decision)
        ]):
            decision = agent.review(base_invoice, valid_report)
            assert decision.status == "REQUIRES_ELEVATED_APPROVAL"
            assert decision.requires_vp_review is True


@patch.object(ApprovalAgent, "_log_observability")
def test_max_retries_exceeded(mock_log, base_invoice, valid_report, tmp_path):
    """Tests that RuntimeError is raised when max retries are exceeded due to persistent policy violations."""
    base_invoice.amount = 15000.0
    valid_report.amount = 15000.0
    
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
        agent = ApprovalAgent(log_path=str(tmp_path / "test.jsonl"))
        
        invalid_decision = ApprovalDecision(
            invoice_vendor="Acme Industrial",
            total_amount=15000.0,
            status="APPROVED",
            requires_vp_review=False,
            decision_notes="Still violating policy."
        )
        
        with patch.object(agent.client.chat.completions, "create", return_value=mock_completion_response(invalid_decision)):
            with pytest.raises(RuntimeError, match="Approval review failed policy constraints"):
                agent.review(base_invoice, valid_report, max_retries=2)
import os
import pytest
from unittest.mock import patch
from src.models import InvoiceData, LineItem, ValidationReport, ItemValidation
from src.approval.reviewer import ApprovalAgent

@pytest.fixture
def base_invoice():
    return InvoiceData(
        invoice_id="INV-TEST", vendor="TestVendor", amount=5000.0, due_date="2026-01-01",
        items=[LineItem(item="WidgetA", quantity=5)]
    )

@pytest.fixture
def valid_report():
    return ValidationReport(
        invoice_id="INV-TEST", is_duplicate=False,
        vendor="TestVendor", amount=5000.0, is_valid=True,
        item_reports=[ItemValidation(item="WidgetA", billed_qty=5, received_qty=5, status="PASS")]
    )

@patch("src.approval.reviewer.ApprovalAgent._generate_critique_notes")
def test_standard_approval_routing(mock_critique, base_invoice, valid_report):
    # Mock the LLM response to save time and API costs
    mock_critique.return_value = "Mocked executive approval notes."
    
    # Needs a dummy API key for initialization bypass during testing
    with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
        agent = ApprovalAgent()
        decision = agent.review(base_invoice, valid_report)
        
        assert decision.status == "APPROVED"
        assert decision.requires_vp_review is False
        assert decision.rejection_reasons is None

@patch("src.approval.reviewer.ApprovalAgent._generate_critique_notes")
def test_vp_threshold_routing(mock_critique, base_invoice, valid_report):
    mock_critique.return_value = "Mocked executive review notes."
    base_invoice.amount = 15000.00  # Pushes it over the $10k limit
    
    with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
        agent = ApprovalAgent()
        decision = agent.review(base_invoice, valid_report)
        
        assert decision.status == "REQUIRES_ELEVATED_APPROVAL"
        assert decision.requires_vp_review is True

@patch("src.approval.reviewer.ApprovalAgent._generate_critique_notes")
def test_rejection_routing(mock_critique, base_invoice):
    mock_critique.return_value = "Mocked executive rejection notes."
    invalid_report = ValidationReport(
        invoice_id="INV-TEST", is_duplicate=False,
        vendor="TestVendor", amount=5000.0, is_valid=False,
        item_reports=[
            ItemValidation(item="WidgetA", billed_qty=10, received_qty=5, status="OVERBILLED", reason="Too many.")
        ]
    )
    
    with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
        agent = ApprovalAgent()
        decision = agent.review(base_invoice, invalid_report)
        
        assert decision.status == "REJECTED"
        assert "Too many." in decision.rejection_reasons
from typing import Optional, Literal
from pydantic import BaseModel

ApprovalStatus = Literal["APPROVED", "REJECTED", "REQUIRES_ELEVATED_APPROVAL"]

class ApprovalDecision(BaseModel):
    invoice_vendor: str
    total_amount: float
    status: ApprovalStatus
    requires_vp_review: bool
    decision_notes: str
    rejection_reasons: Optional[str] = None
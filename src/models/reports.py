from typing import List, Optional
from pydantic import BaseModel

class ItemValidation(BaseModel):
    item: str
    billed_qty: int
    received_qty: Optional[int]
    status: str  # PASS, OVERBILLED, NOT_RECEIVED, INVALID_DATA
    reason: Optional[str] = None

class ValidationReport(BaseModel):
    vendor: str
    amount: float
    is_valid: bool
    item_reports: List[ItemValidation]
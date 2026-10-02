from typing import List, Optional
from pydantic import BaseModel

class ItemValidation(BaseModel):
    item: str
    requested: int
    available: Optional[int]
    status: str  # PASS, INSUFFICIENT_STOCK, UNKNOWN_ITEM, INVALID_DATA, OUT_OF_STOCK
    reason: Optional[str] = None

class ValidationReport(BaseModel):
    vendor: str
    amount: float
    is_valid: bool
    item_reports: List[ItemValidation]
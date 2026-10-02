from typing import List, Optional
from pydantic import BaseModel

class ItemValidation(BaseModel):
    item: str
    billed_qty: int
    received_qty: Optional[int]
    status: str 
    reason: Optional[str] = None

class ValidationReport(BaseModel):
    invoice_id: str          
    is_duplicate: bool       
    vendor: str
    amount: float
    is_valid: bool
    item_reports: List[ItemValidation]
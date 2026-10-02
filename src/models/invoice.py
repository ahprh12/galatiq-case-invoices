from typing import List
from pydantic import BaseModel

class LineItem(BaseModel):
    item: str
    quantity: int

class InvoiceData(BaseModel):
    invoice_id: str
    vendor: str
    amount: float
    due_date: str
    items: List[LineItem]
from typing import List
from pydantic import BaseModel

class LineItem(BaseModel):
    item: str
    quantity: int

class InvoiceData(BaseModel):
    vendor: str
    amount: float
    items: List[LineItem]
    due_date: str
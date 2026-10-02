import os
import json
import pdfplumber
from pydantic import BaseModel
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from the local .env file
load_dotenv()

# 1. Define the Strict Deterministic Schema
class LineItem(BaseModel):
    item: str
    quantity: int

class InvoiceData(BaseModel):
    vendor: str
    amount: float
    items: List[LineItem]
    due_date: str

class ExtractionAgent:
    def __init__(self):
        # Safely fetch the key from the environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("API key not found in .env file. Ask Aakash for details.")
            
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.model = "gemini-3.5-flash-lite"

    def read_file(self, file_path: str) -> str:
        """Parses raw text from various file formats."""
        ext = file_path.lower().split('.')[-1]
        
        if ext in ['txt', 'json', 'csv', 'xml']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif ext == 'pdf':
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            return text
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def extract_invoice(self, file_path: str, max_retries: int = 3) -> InvoiceData:
        """Passes the raw text to the model and enforces the Pydantic schema."""
        raw_text = self.read_file(file_path)
        schema_json = InvoiceData.model_json_schema()

        import time

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a precise data extraction agent. Extract the invoice data "
                                f"into a JSON object matching this schema: {json.dumps(schema_json)}. "
                                "Output ONLY valid JSON."
                            ),
                        },
                        {"role": "user", "content": f"Invoice Text:\n{raw_text}"},
                    ],
                    response_format={"type": "json_object"},
                )
                raw_json = response.choices[0].message.content
                return InvoiceData.model_validate_json(raw_json)

            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    print(f"⚠️ Model busy (503). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise e

# --- Testing the Pipeline ---
if __name__ == "__main__":
    # Instantiate the agent without passing the key. 
    # The __init__ function will safely pull it from your .env file automatically.
    agent = ExtractionAgent()
    
    test_file = "data/invoices/invoice_1001.txt"
    try:
        result = agent.extract_invoice(test_file)
        print("✅ Extraction Successful!")
        print(result.model_dump_json(indent=2))
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
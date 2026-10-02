import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv
from src.models import InvoiceData
from src.ingestion.file_readers import read_document

load_dotenv()

class ExtractionAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file, ask Aakash for details.")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.model = "gemini-3.5-flash-lite"

    def extract_invoice(self, file_path: str, max_retries: int = 3) -> InvoiceData:
        """Parses document text into validated InvoiceData using the LLM."""
        raw_text = read_document(file_path)
        schema_json = InvoiceData.model_json_schema()

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a precise data extraction agent. Extract invoice data "
                                f"into a JSON object matching this schema: {json.dumps(schema_json)}. "
                                "CRUCIAL INSTRUCTIONS: "
                                "1. Locate the exact Invoice Number or ID. If an explicit invoice number is missing, "
                                "create a fallback ID by combining the vendor name and date (e.g., 'VENDOR-YYYYMMDD'). "
                                "2. Output ONLY valid JSON."
                            ),
                        },
                        {"role": "user", "content": f"Invoice Content:\n{raw_text}"},
                    ],
                    response_format={"type": "json_object"},
                )
                raw_json = response.choices[0].message.content
                return InvoiceData.model_validate_json(raw_json)

            except Exception as e:
                if ("503" in str(e) or "429" in str(e)) and attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    time.sleep(wait_time)
                else:
                    raise e
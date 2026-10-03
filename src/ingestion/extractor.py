import os
import json
import time
from datetime import datetime
from openai import OpenAI
from pydantic import ValidationError
from dotenv import load_dotenv
from src.models import InvoiceData
from src.ingestion.file_readers import read_document

load_dotenv()

class ExtractionAgent:
    def __init__(self, log_path: str = os.path.join("data", "llm_observability.jsonl")):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file, ask Aakash for details.")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.model = "gemini-3.5-flash-lite"
        
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def _log_observability(self, file_path: str, attempt: int, messages: list, raw_response: str, error: str = None):
        """Appends the LLM payload, tool call arguments, and errors to a JSONL file."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": "ExtractionAgent",
            "file_processed": file_path,
            "attempt": attempt + 1,
            "messages": [m.model_dump() if hasattr(m, 'model_dump') else m for m in messages],
            "raw_response": raw_response,
            "error": error
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    def extract_invoice(self, file_path: str, max_retries: int = 3) -> InvoiceData:
        """Extracts invoice data by forcing the LLM to call a specific extraction tool."""
        raw_text = read_document(file_path)
        
        # Define the Pydantic schema as an executable tool
        extraction_tool = {
            "type": "function",
            "function": {
                "name": "submit_extracted_invoice",
                "description": "Submit structured data extracted from an invoice document.",
                "parameters": InvoiceData.model_json_schema()
            }
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a precise Accounts Payable extraction agent. Review the document "
                    "and call the 'submit_extracted_invoice' tool with the extracted data. "
                    "Locate the exact Invoice Number or ID. If an explicit invoice number is missing, "
                    "create a fallback ID by combining the vendor name and date (e.g., 'VENDOR-YYYYMMDD')."
                ),
            },
            {"role": "user", "content": f"Invoice Content:\n{raw_text}"},
        ]

        last_exception = None

        for attempt in range(max_retries):
            raw_args = None
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=[extraction_tool],
                    # Force the model to use the tool
                    tool_choice={"type": "function", "function": {"name": "submit_extracted_invoice"}}
                )
                
                message = response.choices[0].message
                
                if not message.tool_calls:
                    raise ValueError("The LLM failed to invoke the extraction tool.")

                tool_call = message.tool_calls[0]
                raw_args = tool_call.function.arguments
                
                # Attempt to validate the tool arguments against the Pydantic schema
                validated_data = InvoiceData.model_validate_json(raw_args)
                
                self._log_observability(file_path, attempt, messages, raw_args, error=None)
                return validated_data

            except ValidationError as e:
                print(f"    ⚠️️ [Extraction] Schema validation failed on attempt {attempt + 1}. Triggering tool self-correction...")
                self._log_observability(file_path, attempt, messages, raw_args, error=str(e))
                
                # Self-Correction: Append the LLM's faulty tool call to the history
                messages.append(message)
                
                # Append a tool response simulating system feedback to prompt a correction
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": f"Validation Error: {str(e)}\n\nPlease correct the arguments and call the tool again."
                })
                
                last_exception = e

            except Exception as e:
                self._log_observability(file_path, attempt, messages, raw_args, error=str(e))
                
                if ("503" in str(e) or "429" in str(e)) and attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    time.sleep(wait_time)
                    last_exception = e
                else:
                    raise e
        
        raise RuntimeError(f"Failed to extract valid invoice data after {max_retries} tool call attempts. Last error: {last_exception}")
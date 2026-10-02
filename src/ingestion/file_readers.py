import pdfplumber

def read_document(file_path: str) -> str:
    """Reads TXT, JSON, CSV, XML, or PDF documents into raw text."""
    ext = file_path.lower().split('.')[-1]

    if ext in ['txt', 'json', 'csv', 'xml']:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    elif ext == 'pdf':
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text
    else:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
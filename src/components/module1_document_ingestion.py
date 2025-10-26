import os
import fitz  # PyMuPDF
from docx import Document

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF"""
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        return text.strip()
    except Exception as e:
        return f"[ERROR] Could not extract PDF: {str(e)}"

def extract_text_from_docx(docx_path):
    """Extract text from DOCX"""
    text = ""
    try:
        doc = Document(docx_path)
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text.strip() + "\n"
        return text.strip()
    except Exception as e:
        return f"[ERROR] Could not extract DOCX: {str(e)}"

def extract_text(file_path):
    """Main text extraction function"""
    if not os.path.exists(file_path):
        return "[ERROR] File not found."
    
    # Determine file type
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext == '.docx':
        return extract_text_from_docx(file_path)
    else:
        return "[ERROR] Unsupported file type. Only PDF and DOCX are supported."

if __name__ == "__main__":
    contract_file = "Contract document.pdf"
    extracted = extract_text(contract_file)
    
    print("=== Extracted Contract Text ===\n")
    print(extracted)
"""
Extract text from SHL catalogue PDF.
Saves extracted text to catalog/catalogue_raw.txt for analysis.
"""
import sys
import json

def extract_pdf(pdf_path: str, output_path: str):
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        total_pages = len(reader.pages)
        print(f"Total pages: {total_pages}")
        
        all_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                all_text.append(f"=== PAGE {i+1} ===\n{text}")
            if i % 10 == 0:
                print(f"  Processed page {i+1}/{total_pages}")
        
        combined = "\n\n".join(all_text)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(combined)
        print(f"Saved {len(combined)} chars to {output_path}")
        return combined
    except Exception as e:
        print(f"Error: {e}")
        return ""

if __name__ == "__main__":
    pdf = sys.argv[1] if len(sys.argv) > 1 else "catlogue.pdf"
    out = sys.argv[2] if len(sys.argv) > 2 else "catalog/catalogue_raw.txt"
    extract_pdf(pdf, out)

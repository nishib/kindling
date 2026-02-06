"""Minimal PDF generator (no reportlab) for environments where reportlab fails."""
import os

# Minimal valid single-page PDF (Welcome to Velora)
PDF_BYTES = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj
4 0 obj << /Length 44 >> stream
BT /F1 24 Tf 100 700 Td (Welcome to Velora - OnboardAI) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
000000206 00000 n
trailer << /Size 5 /Root 1 0 R >>
startxref
304
%%EOF"""


def main():
    os.makedirs("static", exist_ok=True)
    with open("static/onboarding_brief.pdf", "wb") as f:
        f.write(PDF_BYTES)
    print("✅ Minimal PDF generated at static/onboarding_brief.pdf (run generate_pdf.py in venv for full 5-page brief)")


if __name__ == "__main__":
    main()

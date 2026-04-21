import os

def generate_full_pdf(output_path):
    header = b"%PDF-1.1\n"
    
    # Text lines for the documentation
    lines = [
        ("Pagume Bot API Documentation v1.0", 18, 50, 780),
        ("----------------------------------", 12, 50, 765),
        ("1. AUTHENTICATION", 14, 50, 740),
        ("Pass your API key in the 'Authorization' header or as a query parameter.", 10, 50, 725),
        ("- Header: Authorization: Bearer <YOUR_KEY>", 10, 70, 710),
        ("- Query: ?key=<YOUR_KEY>", 10, 70, 695),
        ("", 10, 50, 680),
        ("2. ENDPOINTS", 14, 50, 660),
        ("GET /api/convert - Convert Gregorian <-> Ethiopian.", 10, 50, 645),
        ("  (Required: date=DD/MM/YYYY, to=ethiopian|gregorian)", 9, 70, 630),
        ("GET /api/today   - Fetch current date in both systems.", 10, 50, 615),
        ("GET /api/age     - Calculate precise age from birth date.", 10, 50, 600),
        ("  (Required: birth_date=DD/MM/YYYY)", 9, 70, 585),
        ("", 10, 50, 570),
        ("3. RESPONSE SCHEMA (JSON)", 14, 50, 550),
        ("{", 10, 70, 535),
        ("  \"success\": true,", 10, 70, 520),
        ("  \"data\": { \"result\": \"...\", \"formatted\": \"...\" },", 10, 70, 505),
        ("  \"meta\": { \"timestamp\": \"ISO-8601\" }", 10, 70, 490),
        ("}", 10, 70, 475),
        ("", 10, 50, 460),
        ("4. ERROR HANDLING", 14, 50, 440),
        ("The API returns standard HTTP status codes (401, 429, 400).", 10, 50, 425),
        ("Example Error Response:", 10, 50, 410),
        ("{ \"success\": false, \"error\": { \"code\": \"INVALID_DATE\", \"message\": \"...\" } }", 10, 70, 395),
        ("", 10, 50, 370),
        ("SUPPORT: support@pagumebot.com", 12, 50, 340),
        ("(Downloaded directly from Pagume Bot Dashboard)", 8, 50, 50)
    ]
    
    content_text = b""
    for text, size, x, y in lines:
        if text:
            # Escape parentheses for PDF
            text = text.replace("(", "\\(").replace(")", "\\)")
            content_text += f"BT /F1 {size} Tf {x} {y} Td ({text}) Tj ET\n".encode()

    # Objects
    obj1 = b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    obj2 = b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
    obj3 = b"3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
    obj4 = b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
    obj5 = f"5 0 obj << /Length {len(content_text)} >> stream\n".encode() + content_text + b"endstream\nendobj\n"
    
    pdf_content = header
    offsets = []
    
    for obj in [obj1, obj2, obj3, obj4, obj5]:
        offsets.append(len(pdf_content))
        pdf_content += obj
        
    startxref = len(pdf_content)
    xref = f"xref\n0 {len(offsets)+1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        xref += f"{offset:010d} 00000 n \n".encode()
    
    pdf_content += xref
    pdf_content += b"trailer << /Size " + str(len(offsets)+1).encode() + b" /Root 1 0 R >>\n"
    pdf_content += b"startxref\n" + str(startxref).encode() + b"\n%%EOF\n"
    
    with open(output_path, "wb") as f:
        f.write(pdf_content)
    print(f"Full documentation PDF generated at: {output_path} ({len(pdf_content)} bytes)")

if __name__ == "__main__":
    generate_full_pdf("assets/api_guide.pdf")

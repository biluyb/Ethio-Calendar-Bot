import os

def generate_minimal_pdf(output_path):
    # This is a minimal valid PDF 1.1 template
    # It contains a single page with text.
    header = b"%PDF-1.1\n"
    
    # Object 1: Catalog
    obj1 = b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    # Object 2: Page List
    obj2 = b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
    
    # Text to display
    content_text = b"BT /F1 18 Tf 50 750 Td (Pagume Bot API Guide v1.0) Tj ET\n"
    content_text += b"BT /F1 12 Tf 50 720 Td (Congratulations! You have received the official documentation.) Tj ET\n"
    content_text += b"BT /F1 12 Tf 50 705 Td (For support, contact us at support@pagumebot.com) Tj ET\n"
    content_text += b"BT /F1 10 Tf 50 670 Td (Full documentation with JSON schemas and examples is) Tj ET\n"
    content_text += b"BT /F1 10 Tf 50 655 Td (coming soon in the next major version update.) Tj ET\n"
    
    stream_len = len(content_text)
    
    # Object 3: Page
    obj3 = b"3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
    # Object 4: Font
    obj4 = b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
    # Object 5: Content Stream
    obj5 = b"5 0 obj << /Length " + str(stream_len).encode() + b" >> stream\n" + content_text + b"endstream\nendobj\n"
    
    # Build the file
    pdf_content = header
    offsets = []
    
    offsets.append(len(pdf_content))
    pdf_content += obj1
    
    offsets.append(len(pdf_content))
    pdf_content += obj2
    
    offsets.append(len(pdf_content))
    pdf_content += obj3
    
    offsets.append(len(pdf_content))
    pdf_content += obj4
    
    offsets.append(len(pdf_content))
    pdf_content += obj5
    
    startxref = len(pdf_content)
    
    # Xref table
    xref = b"xref\n0 6\n"
    xref += b"0000000000 65535 f \n"
    for offset in offsets:
        xref += f"{offset:010d} 00000 n \n".encode()
    
    pdf_content += xref
    
    # Trailer
    pdf_content += b"trailer << /Size 6 /Root 1 0 R >>\n"
    pdf_content += b"startxref\n"
    pdf_content += str(startxref).encode() + b"\n"
    pdf_content += b"%%EOF\n"
    
    with open(output_path, "wb") as f:
        f.write(pdf_content)
    print(f"PDF generated at: {output_path} (Size: {len(pdf_content)} bytes)")

if __name__ == "__main__":
    current_dir = os.getcwd()
    assets_dir = os.path.join(current_dir, "assets")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
    generate_minimal_pdf(os.path.join(assets_dir, "api_guide.pdf"))

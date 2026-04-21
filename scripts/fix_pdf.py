import os

def generate_pro_pdf(output_path):
    header = b"%PDF-1.1\n"
    
    # Define content for each page
    pages_content = [
        # Page 1: Title & Overview
        [
            ("Pagume Bot API Documentation", 24, 150, 750),
            ("Building the Future of Ethiopian Calendar Services", 12, 160, 730),
            ("Version: 1.0.0 | Release: May 2026", 10, 200, 715),
            ("----------------------------------------------------------------", 12, 50, 680),
            ("OVERVIEW", 16, 50, 640),
            ("Pagume Bot is the industry leader in Ethiopian calendar intelligence.", 11, 50, 615),
            ("This API allows developers to integrate high-precision date", 11, 50, 600),
            ("conversions, age calculations, and cultural dating data into", 11, 50, 585),
            ("their own applications, websites, and enterprise systems.", 11, 50, 570),
            ("KEY FEATURES:", 12, 50, 530),
            ("- High Precision Gregorian-Ethiopian conversion", 10, 70, 510),
            ("- Real-time Ethiopian 'Today' data", 10, 70, 495),
            ("- Precise Age calculations (Years, Months, Days)", 10, 70, 480),
            ("- JSON standardized responses", 10, 70, 465),
            ("© 2026 Pagume Bot Team", 9, 250, 50)
        ],
        # Page 2: Authentication
        [
            ("1. AUTHENTICATION & SECURITY", 18, 50, 780),
            ("Security is our top priority. All requests must be authenticated.", 11, 50, 750),
            ("1.1 API KEYS", 14, 50, 710),
            ("Generate your unique developer key via the Pagume Bot dashboard.", 10, 50, 690),
            ("Keep this key secret. If compromised, revoke it immediately.", 10, 50, 675),
            ("1.2 HEADER AUTHENTICATION (Recommended)", 14, 50, 630),
            ("Authorization: Bearer <YOUR_API_KEY>", 11, 70, 610),
            ("1.3 QUERY AUTHENTICATION", 14, 50, 570),
            ("GET /v1/endpoint?key=<YOUR_API_KEY>", 11, 70, 550),
            ("Note: Header auth is preferred to avoid key exposure in logs.", 10, 50, 520),
            ("Page 2 of 5", 9, 280, 50)
        ],
        # Page 3: Endpoints
        [
            ("2. CORE API ENDPOINTS", 18, 50, 780),
            ("2.1 /api/convert", 14, 50, 740),
            ("Converts dates between calendar systems.", 10, 50, 725),
            ("Params: date (DD/MM/YYYY), to (ethiopian|gregorian)", 10, 70, 710),
            ("2.2 /api/today", 14, 50, 670),
            ("Returns the current date in both systems simultaneously.", 10, 50, 655),
            ("No additional parameters required.", 10, 70, 640),
            ("2.3 /api/age", 14, 50, 600),
            ("Calculates age based on birth date.", 10, 50, 585),
            ("Params: birth_date (DD/MM/YYYY), calendar (input type)", 10, 70, 570),
            ("Default calendar is gregorian.", 9, 70, 555),
            ("Page 3 of 5", 9, 280, 50)
        ],
        # Page 4: Schemas
        [
            ("3. JSON DATA SCHEMAS", 18, 50, 780),
            ("All responses follow a predictable structure.", 11, 50, 750),
            ("3.1 SUCCESS ENVELOPE", 14, 50, 710),
            ("{", 10, 70, 690),
            ("  \"success\": true,", 10, 70, 675),
            ("  \"data\": { ... },", 10, 70, 660),
            ("  \"meta\": { \"timestamp\": \"ISO-8601\" }", 10, 70, 645),
            ("}", 10, 70, 630),
            ("3.2 ERROR ENVELOPE", 14, 50, 590),
            ("{", 10, 70, 570),
            ("  \"success\": false,", 10, 70, 555),
            ("  \"error\": {", 10, 70, 540),
            ("    \"code\": \"INVALID_DATE\",", 10, 90, 525),
            ("    \"message\": \"Please use DD/MM/YYYY format.\"", 10, 90, 510),
            ("  }", 10, 70, 495),
            ("}", 10, 70, 480),
            ("Page 4 of 5", 9, 280, 50)
        ],
        # Page 5: Support & Limits
        [
            ("4. RATE LIMITING & SUPPORT", 18, 50, 780),
            ("4.1 USAGE QUOTAS", 14, 50, 740),
            ("Standard keys are limited to 30 requests per minute.", 11, 50, 715),
            ("Exceeding this results in a 429 Too Many Requests error.", 10, 50, 700),
            ("4.2 ENTERPRISE SOLUTIONS", 14, 50, 660),
            ("For higher quotas, custom feature requests, or massive scale:", 10, 50, 640),
            ("Email: support@pagumebot.com", 12, 70, 620),
            ("4.3 COMMUNITY & FEEDBACK", 14, 50, 580),
            ("Join our developer community on Telegram for updates.", 10, 50, 560),
            ("We value your feedback to improve our conversion logic.", 10, 50, 545),
            ("Stay tuned for v2.0 with lunar cycle support!", 11, 50, 500),
            ("Page 5 of 5", 9, 280, 50)
        ]
    ]
    
    # 1. Objects initialization
    objects = []
    
    # Catalog (Object 1) -> Pages (Object 2)
    catalog = b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    # Placeholder for Pages (Object 2)
    # obj3 is the start of individual Page objects
    page_ids = [str(i+3) for i in range(len(pages_content))]
    pages_root = f"2 0 obj << /Type /Pages /Kids [{' 0 R '.join(page_ids)} 0 R] /Count {len(pages_content)} >> endobj\n".encode()
    
    objects.append(catalog)
    objects.append(pages_root)
    
    # Standard Font (Object 4, we define it once)
    font_id = 100 # Choosing a high ID to avoid conflicts
    font_obj = f"{font_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n".encode()
    
    page_objs = []
    content_objs = []
    
    # Next free ID starts after font and other base objects
    next_id = 3
    
    for i in range(len(pages_content)):
        page_id = next_id
        content_id = next_id + len(pages_content)
        
        # Page Object: points to its specific content stream
        page_obj = f"{page_id} 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >> endobj\n".encode()
        page_objs.append(page_obj)
        
        # Content Stream
        lines = pages_content[i]
        stream_data = b""
        for text, size, x, y in lines:
            text_esc = text.replace("(", "\\(").replace(")", "\\)")
            stream_data += f"BT /F1 {size} Tf {x} {y} Td ({text_esc}) Tj ET\n".encode()
            
        content_obj = f"{content_id} 0 obj << /Length {len(stream_data)} >> stream\n".encode() + stream_data + b"endstream\nendobj\n"
        content_objs.append(content_obj)
        next_id += 1
        
    # Order: [Catalog, PagesRoot, Font, Page1, Page2..., Content1, Content2...]
    all_objs = [catalog, pages_root, font_obj] + page_objs + content_objs
    
    # Build final binary
    pdf_content = header
    offsets = []
    
    # We need to map object IDs correctly for the xref
    # Catalog is 1, PagesRoot is 2, Font is 100, Pages are 3..7, Contents are 8..12
    # xref table must be ordered by object ID
    obj_dict = {
        1: catalog,
        2: pages_root,
        font_id: font_obj
    }
    for i, p in enumerate(page_objs): obj_dict[3 + i] = p
    for i, c in enumerate(content_objs): obj_dict[3 + len(page_objs) + i] = c
    
    final_sorted_ids = sorted(obj_dict.keys())
    
    # We need a continuous sequence or empty slots for xref
    # Actually, simplest is to just use IDs 1 to N
    # Let's re-ID everything strictly 1 to N
    
    strict_objs = [catalog, pages_root] # 1, 2
    # Let's put pages 3..7
    # contents 8..12
    # font 13
    
    font_id = 3 + 2 * len(pages_content)
    strict_objs = [
        catalog, # 1
        pages_root # 2
    ]
    # Re-calculate pages root with strict IDs
    page_ids = [str(i+3) for i in range(len(pages_content))]
    pages_root = f"2 0 obj << /Type /Pages /Kids [{' 0 R '.join(page_ids)} 0 R] /Count {len(pages_content)} >> endobj\n".encode()
    strict_objs[1] = pages_root
    
    pages = []
    contents = []
    for i in range(len(pages_content)):
        p_id = 3 + i
        c_id = 3 + len(pages_content) + i
        pages.append(f"{p_id} 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {c_id} 0 R >> endobj\n".encode())
        
        lines = pages_content[i]
        stream_data = b""
        for text, size, x, y in lines:
            text_esc = text.replace("(", "\\(").replace(")", "\\)")
            stream_data += f"BT /F1 {size} Tf {x} {y} Td ({text_esc}) Tj ET\n".encode()
        contents.append(f"{c_id} 0 obj << /Length {len(stream_data)} >> stream\n".encode() + stream_data + b"endstream\nendobj\n")
        
    font_obj = f"{font_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n".encode()
    
    final_objs = strict_objs + pages + contents + [font_obj]
    
    pdf_content = header
    offsets = []
    for obj in final_objs:
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
    print(f"5-Page Professional PDF generated at: {output_path} ({len(pdf_content)} bytes)")

if __name__ == "__main__":
    generate_pro_pdf("assets/api_guide.pdf")

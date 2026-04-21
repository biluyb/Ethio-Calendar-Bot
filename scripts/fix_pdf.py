import os

def generate_premium_pdf(output_path):
    header = b"%PDF-1.1\n"
    
    # Colors (R G B)
    BLUE = "0.0 0.53 0.8"
    DARK_BLUE = "0.1 0.24 0.31"
    GRAY = "0.4 0.45 0.55"
    LIGHT_BLUE = "0.93 0.96 1.0"
    GREEN = "0.13 0.77 0.37"
    
    # Content per page
    # Tuple format: (type, content, size, x, y, color)
    # Types: 'text', 'rect' (x, y, w, h), 'line' (x1, y1, x2, y2)
    pages_content = [
        # Page 1: COVER LETTER
        [
            ('rect', (0, 0, 595, 842), None, 0, 0, LIGHT_BLUE), # Background
            ('rect', (0, 750, 595, 92), None, 0, 0, BLUE),      # Header Bar
            ('text', "PAGUME BOT SERVICES", 26, 150, 780, "1 1 1"), # White text on blue
            ('text', "Date: April 21, 2026", 11, 450, 700, DARK_BLUE),
            ('text', "To: Our Valued Developer Community", 13, 50, 650, DARK_BLUE),
            ('text', "Subject: Official Release of Pagume API v1.0", 14, 50, 620, DARK_BLUE),
            ('text', "Dear Developer,", 12, 50, 570, DARK_BLUE),
            ('text', "We are thrilled to present the first official documentation for the Pagume Bot API.", 11, 50, 545, DARK_BLUE),
            ('text', "Pagume Bot was built with a single mission: to provide the most precise and accessible", 11, 50, 530, DARK_BLUE),
            ('text', "Ethiopian calendar tools in the digital era. As we grow, our API becomes the backbone", 11, 50, 515, DARK_BLUE),
            ('text', "for countless integrations, from mobile apps to corporate scheduling systems.", 11, 50, 500, DARK_BLUE),
            ('text', "This guide outlines everything you need to start building. We look forward to seeing", 11, 50, 475, DARK_BLUE),
            ('text', "what you create with Pagume.", 11, 50, 460, DARK_BLUE),
            ('text', "Sincerely,", 12, 50, 380, DARK_BLUE),
            ('text', "The Pagume Bot Leadership Team", 12, 50, 360, BLUE),
            ('rect', (50, 100, 495, 2), None, 0, 0, GRAY), # Separator
            ('text', "© 2026 Pagume Bot Team | support@pagumebot.com", 9, 180, 50, GRAY)
        ],
        # Page 2: TITLE & OVERVIEW
        [
            ('rect', (0, 700, 595, 142), None, 0, 0, DARK_BLUE),
            ('text', "Pagume Bot API Documentation", 28, 90, 770, "1 1 1"),
            ('text', "Official Developer Guide | v1.0.0", 12, 210, 745, "0.8 0.8 0.8"),
            ('text', "OVERVIEW", 18, 50, 650, BLUE),
            ('rect', (50, 642, 100, 3), None, 0, 0, BLUE),
            ('text', "Pagume Bot is the industry standard for Ethiopian calendar intelligence.", 11, 50, 610, DARK_BLUE),
            ('text', "Our API enables high-fidelity conversions and precise age calculations,", 11, 50, 595, DARK_BLUE),
            ('text', "powering a new generation of localized digital solutions.", 11, 50, 580, DARK_BLUE),
            ('text', "KEY CAPABILITIES:", 13, 50, 540, DARK_BLUE),
            ('text', "- High Precision Gregorian-Ethiopian conversion", 11, 70, 515, GREEN),
            ('text', '- Real-time sync with traditional Ethiopian timekeeping', 11, 70, 495, GREEN),
            ('text', '- Multi-language support (Amharic & English)', 11, 70, 475, GREEN),
            ('text', '- Enterprise-grade JSON standard output', 11, 70, 455, GREEN),
            ('text', "Page 1 of 5 | Pagume documentation", 9, 230, 40, GRAY)
        ],
        # Page 3: AUTHENTICATION
        [
            ('rect', (50, 760, 495, 30), None, 0, 0, LIGHT_BLUE),
            ('text', "1. AUTHENTICATION & SECURITY", 18, 50, 765, BLUE),
            ('text', "All requests must be authenticated using a unique API Key.", 11, 50, 730, DARK_BLUE),
            ('text', "1.1 HEADER METHOD (Recommended)", 14, 50, 690, BLUE),
            ('rect', (70, 655, 400, 25), None, 0, 0, "0.1 0.1 0.1"), # Dark code block background
            ('text', "Authorization: Bearer <YOUR_API_KEY>", 11, 90, 662, "1 1 1"),
            ('text', "Using headers ensures your keys are not exposed in server logs.", 10, 50, 630, GRAY),
            ('text', "1.2 QUERY METHOD", 14, 50, 580, BLUE),
            ('rect', (70, 545, 400, 25), None, 0, 0, "0.1 0.1 0.1"),
            ('text', "GET /v1/endpoint?key=<YOUR_API_KEY>", 11, 90, 552, "1 1 1"),
            ('text', "1.3 ACCESS CONTROL", 14, 50, 500, BLUE),
            ('text', "Keys are tied to your Telegram account. Never share them.", 11, 50, 480, DARK_BLUE),
            ('text', "Page 2 of 5 | Pagume documentation", 9, 230, 40, GRAY)
        ],
        # Page 4: ENDPOINTS
        [
            ('text', "2. CORE ENDPOINTS", 18, 50, 780, BLUE),
            ('text', "2.1 /api/convert", 15, 50, 745, BLUE),
            ('text', "Parameters:", 11, 70, 720, DARK_BLUE),
            ('text', "- date: DD/MM/YYYY (Required)", 10, 90, 705, DARK_BLUE),
            ('text', "- to: ethiopian | gregorian (Required)", 10, 90, 690, DARK_BLUE),
            ('text', "2.2 /api/today", 15, 50, 640, BLUE),
            ('text', "Fetches current date in both calendar systems.", 11, 70, 615, DARK_BLUE),
            ('text', "2.3 /api/age", 15, 50, 560, BLUE),
            ('text', "Calculate years, months, and days from birth date.", 11, 70, 535, DARK_BLUE),
            ('text', "Parameters:", 11, 70, 510, DARK_BLUE),
            ('text', "- birth_date: DD/MM/YYYY (Required)", 10, 90, 495, DARK_BLUE),
            ('text', "- calendar: gregorian | ethiopian", 10, 90, 480, DARK_BLUE),
            ('text', "Page 3 of 5 | Pagume documentation", 9, 230, 40, GRAY)
        ],
        # Page 5: SCHEMAS
        [
            ('text', "3. JSON SCHEMAS", 18, 50, 780, BLUE),
            ('text', "3.1 Success Format", 14, 50, 745, BLUE),
            ('rect', (50, 630, 495, 100), None, 0, 0, "0.1 0.1 0.1"),
            ('text', "{", 10, 70, 715, "1 1 1"),
            ('text', "  \"success\": true,", 10, 70, 700, "1 1 1"),
            ('text', "  \"data\": { \"result\": \"...\" },", 10, 70, 685, "1 1 1"),
            ('text', "  \"meta\": { \"timestamp\": \"ISO-8601\" }", 10, 70, 670, "1 1 1"),
            ('text', "}", 10, 70, 655, "1 1 1"),
            ('text', "3.2 Error Format", 14, 50, 580, BLUE),
            ('rect', (50, 480, 495, 85), None, 0, 0, "0.1 0.1 0.1"),
            ('text', "{", 10, 70, 550, "1 1 1"),
            ('text', "  \"success\": false,", 10, 70, 535, "1 1 1"),
            ('text', "  \"error\": { \"code\": \"...\", \"message\": \"...\" }", 10, 70, 520, "1 1 1"),
            ('text', "}", 10, 70, 505, "1 1 1"),
            ('text', "Page 4 of 5 | Pagume documentation", 9, 230, 40, GRAY)
        ],
        # Page 6: LIMITS & CLOSING
        [
            ('text', "4. RATE LIMITS & BEST PRACTICES", 18, 50, 780, BLUE),
            ('text', "Standard rate limit: 30 requests per minute.", 11, 50, 750, DARK_BLUE),
            ('text', "- Implement local caching to reduce API hits.", 10, 70, 725, DARK_BLUE),
            ('text', '- Use standard DD/MM/YYYY formatting.', 10, 70, 710, DARK_BLUE),
            ('text', '- Verify API keys before bulk deployment.', 10, 70, 695, DARK_BLUE),
            ('text', "Thank you for choosing Pagume Bot.", 14, 160, 550, BLUE),
            ('text', "We are constantly evolving to serve you better.", 11, 165, 530, DARK_BLUE),
            ('rect', (150, 510, 300, 1), None, 0, 0, GRAY),
            ('text', "Pagume Team Development", 10, 240, 490, GRAY),
            ('text', "Official Support: support@pagumebot.com", 11, 180, 200, BLUE),
            ('text', "Page 5 of 5 | Pagume documentation", 9, 230, 40, GRAY)
        ]
    ]

    # PDF Binary components
    pdf_objs = []
    
    # 1. Catalog
    pdf_objs.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    
    # 2. Page List
    page_ids = [str(i+3) for i in range(len(pages_content))]
    pdf_objs.append(f"2 0 obj << /Type /Pages /Kids [{' 0 R '.join(page_ids)} 0 R] /Count {len(pages_content)} >> endobj\n".encode())
    
    # Font (Dedicated ID)
    font_id = 3 + 2 * len(pages_content)
    
    for i in range(len(pages_content)):
        p_id = 3 + i
        c_id = 3 + len(pages_content) + i
        
        # 3. Page Object
        pdf_objs.append(f"{p_id} 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {c_id} 0 R >> endobj\n".encode())
        
        # 4. Content Stream
        stream_data = b""
        lines = pages_content[i]
        for type, val, size, x, y, color in lines:
            if type == 'text':
                text_esc = val.replace("(", "\\(").replace(")", "\\)")
                stream_data += f"q {color} rg BT /F1 {size} Tf {x} {y} Td ({text_esc}) Tj ET Q\n".encode()
            elif type == 'rect':
                rx, ry, rw, rh = val
                stream_data += f"q {color} rg {rx} {ry} {rw} {rh} re f Q\n".encode()
            elif type == 'line':
                x1, y1, x2, y2 = val
                stream_data += f"q {color} RG {x1} {y1} m {x2} {y2} l S Q\n".encode()
                
        pdf_objs.append(f"{c_id} 0 obj << /Length {len(stream_data)} >> stream\n".encode() + stream_data + b"endstream\nendobj\n")
        
    # 5. Font Object
    pdf_objs.append(f"{font_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n".encode())
    
    # Final Write
    pdf_binary = header
    offsets = []
    for obj in pdf_objs:
        offsets.append(len(pdf_binary))
        pdf_binary += obj
        
    startxref = len(pdf_binary)
    xref = f"xref\n0 {len(offsets)+1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        xref += f"{offset:010d} 00000 n \n".encode()
    
    pdf_binary += xref
    pdf_binary += b"trailer << /Size " + str(len(offsets)+1).encode() + b" /Root 1 0 R >>\n"
    pdf_binary += b"startxref\n" + str(startxref).encode() + b"\n%%EOF\n"
    
    with open(output_path, "wb") as f:
        f.write(pdf_binary)
    print(f"Premium colorful 6-page PDF generated at {output_path} ({len(pdf_binary)} bytes)")

if __name__ == "__main__":
    generate_premium_pdf("assets/api_guide.pdf")

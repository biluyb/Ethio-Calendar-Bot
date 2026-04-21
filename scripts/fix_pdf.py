"""
Pagume Bot API Guide - Professional 5-Page PDF Generator
Generates a well-laid-out, colorful, deeply explained documentation PDF.
"""

def escape(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def text(x, y, txt, size=10, r=0, g=0, b=0, bold=False):
    font = "/F2" if bold else "/F1"
    return f"BT {r:.2f} {g:.2f} {b:.2f} rg {font} {size} Tf {x} {y} Td ({escape(txt)}) Tj ET\n"

def rect(x, y, w, h, r, g, b):
    return f"{r:.2f} {g:.2f} {b:.2f} rg {x} {y} {w} {h} re f\n"

def line(x1, y1, x2, y2, r=0.6, g=0.6, b=0.6, width=0.5):
    return f"{width} w {r:.2f} {g:.2f} {b:.2f} RG {x1} {y1} m {x2} {y2} l S\n"

# Brand Colors  
BL = (0.0, 0.44, 0.75)   # Pagume Blue
DB = (0.07, 0.18, 0.28)  # Dark Blue
GR = (0.10, 0.65, 0.38)  # Green
GY = (0.45, 0.50, 0.57)  # Gray
WH = (1.0, 1.0, 1.0)     # White
LB = (0.93, 0.96, 1.00)  # Light Blue
LG = (0.93, 1.00, 0.95)  # Light Green
LY = (0.99, 0.97, 0.90)  # Light Yellow

BASE = "https://ethio-calendar-bot.onrender.com"

def build_page(streams):
    return "".join(streams)

def finalize_pdf(pages_streams):
    """Build a valid multi-page PDF from a list of page content streams."""
    header = b"%PDF-1.4\n"
    n_pages = len(pages_streams)
    font_id = 3 + n_pages * 2  # IDs: 1=catalog, 2=pages, 3..=page objs, then content, then font

    # Object 1: Catalog
    obj1 = b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    # Object 2: Pages root
    kids = " ".join(f"{3+i} 0 R" for i in range(n_pages))
    obj2 = f"2 0 obj << /Type /Pages /Kids [{kids}] /Count {n_pages} >> endobj\n".encode()

    all_objs = [obj1, obj2]
    
    page_objs = []
    content_objs = []
    
    for i, stream in enumerate(pages_streams):
        p_id = 3 + i
        c_id = 3 + n_pages + i
        encoded = stream.encode("latin-1", errors="replace")
        
        page_obj = (
            f"{p_id} 0 obj << /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_id} 0 R /F2 {font_id+1} 0 R >> >> "
            f"/Contents {c_id} 0 R >> endobj\n"
        ).encode()
        page_objs.append(page_obj)
        
        content_obj = (
            f"{c_id} 0 obj << /Length {len(encoded)} >> stream\n"
        ).encode() + encoded + b"\nendstream\nendobj\n"
        content_objs.append(content_obj)

    font_reg = f"{font_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >> endobj\n".encode()
    font_bold = f"{font_id+1} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >> endobj\n".encode()
    
    all_objs += page_objs + content_objs + [font_reg, font_bold]
    
    pdf = header
    offsets = []
    for obj in all_objs:
        offsets.append(len(pdf))
        pdf += obj
    
    startxref = len(pdf)
    xref = f"xref\n0 {len(offsets)+1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()
    
    pdf += xref
    pdf += f"trailer << /Size {len(offsets)+1} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF\n".encode()
    return pdf


def page1_cover():
    """Cover Page"""
    s = ""
    # Full dark background
    s += rect(0, 0, 595, 842, *DB)
    # Blue header bar
    s += rect(0, 680, 595, 162, *BL)
    # Decorative bottom strip
    s += rect(0, 0, 595, 80, *BL)
    # Accent line
    s += rect(50, 670, 495, 4, *WH)

    # Title block
    s += text(57, 800, "PAGUME BOT API", 34, *WH, bold=True)
    s += text(57, 760, "Developer Documentation & Integration Guide", 14, 0.8, 0.9, 1.0)
    s += text(57, 738, "Version 1.0  |  Released May 2026", 11, 0.7, 0.8, 0.9)

    # Cover letter body
    s += text(57, 638, "A Letter to Our Developer Community", 16, *WH, bold=True)
    s += rect(57, 625, 80, 2, *GR)

    body_lines = [
        ("Dear Developer,", True, 14, WH),
        ("", False, 10, WH),
        ("We are proud to release the first official version of the Pagume Bot Developer API.", False, 11, (0.85, 0.92, 1.0)),
        ("Pagume Bot was built on a singular mission: to make Ethiopian calendar intelligence", False, 11, (0.85, 0.92, 1.0)),
        ("accessible to every developer, startup, and enterprise in the world.", False, 11, (0.85, 0.92, 1.0)),
        ("", False, 10, WH),
        ("This document is your complete reference guide. Within these pages you will find", False, 11, (0.85, 0.92, 1.0)),
        ("everything from generating an API key to handling edge-case errors in production.", False, 11, (0.85, 0.92, 1.0)),
        ("", False, 10, WH),
        ("We built this API for builders. We hope it helps you ship something meaningful.", False, 11, (0.85, 0.92, 1.0)),
        ("", False, 10, WH),
        ("Sincerely,", False, 12, WH),
        ("The Pagume Bot Team", True, 13, (0.4, 0.8, 1.0)),
    ]
    
    y = 590
    for line_text, is_bold, size, color in body_lines:
        s += text(57, y, line_text, size, *color, bold=is_bold)
        y -= (size + 7)

    # Footer
    s += text(170, 40, "(c) 2026 Pagume Bot  |  support@pagumebot.com", 10, 0.7, 0.8, 0.9)
    s += text(270, 22, "Cover Page", 9, 0.5, 0.6, 0.7)
    return s


def page2_overview():
    """Page 2: Overview & How It Works"""
    s = ""
    # Top bar
    s += rect(0, 800, 595, 42, *BL)
    s += text(20, 813, "PAGUME BOT API  |  Developer Guide  |  v1.0", 11, *WH, bold=True)

    s += text(50, 762, "Overview", 22, *DB, bold=True)
    s += rect(50, 754, 120, 3, *BL)

    overview = [
        "Pagume Bot is the most advanced Ethiopian calendar service on Telegram.",
        "Our REST API unlocks this power for your applications, letting you:",
        "",
        " - Convert any date between Gregorian and Ethiopian calendars in real-time.",
        " - Retrieve today's date in both systems with a single request.",
        " - Calculate precise age (years, months, days) from any birth date.",
        "",
        "The API is stateless, JSON-based, and designed for simplicity. There are no",
        "SDKs required - any HTTP client (curl, Python requests, fetch) works directly.",
    ]
    y = 730
    for l in overview:
        s += text(50, y, l, 11, *DB)
        y -= 18

    # How It Works Box
    s += rect(50, 540, 495, 28, *BL)
    s += text(57, 550, "How It Works", 14, *WH, bold=True)
    steps = [
        ("1", "Generate your API key via the Pagume Bot on Telegram (/apikey)."),
        ("2", "Make a GET request to the endpoint with your key and parameters."),
        ("3", "Receive a structured JSON response with your converted or calculated data."),
        ("4", "Handle the 'success' flag in the response to detect errors gracefully."),
    ]
    y = 520
    for num, desc in steps:
        s += rect(50, y-4, 22, 20, *GR)
        s += text(57, y+2, num, 11, *WH, bold=True)
        s += text(82, y+2, desc, 11, *DB)
        y -= 28

    # Base URL section
    s += rect(50, 360, 495, 28, *DB)
    s += text(57, 371, "Base URL (All Endpoints)", 13, *WH, bold=True)
    s += rect(50, 320, 495, 34, 0.96, 0.97, 0.99)
    s += rect(50, 320, 5, 34, *BL)
    s += text(63, 332, BASE, 12, *BL, bold=True)

    s += text(50, 300, "All endpoints are accessed via HTTPS GET requests against this base URL.", 10, *GY)
    s += text(50, 285, "The server is hosted on Render and auto-restarts on updates.", 10, *GY)

    # Footer
    s += rect(0, 0, 595, 22, *DB)
    s += text(240, 7, "Page 1 of 4  |  Pagume API", 9, *WH)
    return s


def page3_auth():
    """Page 3: Authentication & Security"""
    s = ""
    s += rect(0, 800, 595, 42, *BL)
    s += text(20, 813, "PAGUME BOT API  |  Developer Guide  |  v1.0", 11, *WH, bold=True)

    s += text(50, 762, "Authentication & Security", 22, *DB, bold=True)
    s += rect(50, 754, 200, 3, *BL)

    s += text(50, 730, "Every API request must include a valid API key. Keys are personal, unique,", 11, *DB)
    s += text(50, 713, "and tied to your Telegram account. Never share your key publicly.", 11, *DB)

    # Method 1
    s += rect(50, 678, 495, 26, *DB)
    s += text(57, 688, "Method 1: Authorization Header (Recommended for Production)", 12, *WH, bold=True)
    s += text(50, 656, "Pass your key in the HTTP request header. This keeps it out of browser history,", 11, *DB)
    s += text(50, 639, "server logs, and URLs. This is the industry-standard practice.", 11, *DB)
    s += rect(50, 600, 495, 32, 0.94, 0.96, 0.99)
    s += rect(50, 600, 5, 32, *BL)
    s += text(63, 622, "Authorization: Bearer YOUR_API_KEY", 11, *BL, bold=True)
    s += text(63, 607, "Example: Authorization: Bearer ec_3094f038a21d8904dfa730f4", 10, *GY)

    # Method 2
    s += rect(50, 565, 495, 26, *DB)
    s += text(57, 575, "Method 2: Query Parameter (Quick testing only)", 12, *WH, bold=True)
    s += text(50, 543, "Append ?key=YOUR_API_KEY to the URL. Easy for quick tests, but avoid in", 11, *DB)
    s += text(50, 526, "production as keys may be exposed in logs or browser history.", 11, *DB)
    s += rect(50, 488, 495, 32, 0.94, 0.96, 0.99)
    s += rect(50, 488, 5, 32, *BL)
    s += text(63, 510, f"{BASE}/api/today?key=YOUR_API_KEY", 11, *BL, bold=True)
    
    # Security Tips
    s += rect(50, 455, 495, 26, *GR)
    s += text(57, 466, "Security Best Practices", 13, *WH, bold=True)
    tips = [
        "Store your API key in environment variables, never in source code.",
        "Rotate your key immediately via the bot if you suspect it is compromised.",
        "Use the Authorization header in all server-to-server or production calls.",
        "Rate limit applies per key: 30 requests per minute. Cache responses when possible.",
    ]
    y = 435
    for tip in tips:
        s += text(63, y, "  -  " + tip, 10, *DB)
        y -= 18

    s += rect(0, 0, 595, 22, *DB)
    s += text(240, 7, "Page 2 of 4  |  Pagume API", 9, *WH)
    return s


def page4_endpoints():
    """Page 4: Endpoint Reference"""
    s = ""
    s += rect(0, 800, 595, 42, *BL)
    s += text(20, 813, "PAGUME BOT API  |  Developer Guide  |  v1.0", 11, *WH, bold=True)

    s += text(50, 762, "API Endpoint Reference", 22, *DB, bold=True)
    s += rect(50, 754, 175, 3, *BL)

    def endpoint_block(y, method, path, desc, params, example_url, note=""):
        nonlocal s
        # Method badge + Path
        s += rect(50, y-2, 40, 18, *GR)
        s += text(55, y+3, method, 10, *WH, bold=True)
        s += text(95, y+3, path, 13, *BL, bold=True)
        y -= 22
        s += text(50, y, desc, 10, *DB)
        y -= 20
        # Params
        s += text(50, y, "Parameters:", 10, *DB, bold=True)
        y -= 16
        for pname, preq, pdesc in params:
            req_col = (0.8, 0.1, 0.1) if preq == "Required" else GY
            s += text(60, y, pname, 10, *BL, bold=True)
            s += text(150, y, f"({preq})", 9, *req_col)
            s += text(230, y, pdesc, 10, *DB)
            y -= 15
        y -= 5
        # Example
        s += text(50, y, "Example:", 10, *DB, bold=True)
        y -= 16
        s += rect(50, y-4, 495, 18, 0.95, 0.97, 1.0)
        s += text(55, y+1, example_url, 9, *DB, bold=True)
        y -= 22
        if note:
            s += text(50, y, "Note: " + note, 9, *GY)
            y -= 15
        return y

    y = 730
    y = endpoint_block(y, "GET", "/api/convert",
        "Converts a date from one calendar system to another.",
        [
            ("date", "Required", "Date in DD/MM/YYYY format (e.g. 21/04/2026)"),
            ("to", "Required", "Target calendar: 'ethiopian' or 'gregorian'"),
        ],
        f"{BASE}/api/convert?date=21/04/2026&to=ethiopian&key=YOUR_KEY"
    )
    y -= 8

    y = endpoint_block(y, "GET", "/api/today",
        "Returns the current date in both Gregorian and Ethiopian calendars.",
        [("(none)", "—", "No extra parameters required.")],
        f"{BASE}/api/today?key=YOUR_KEY"
    )
    y -= 8

    y = endpoint_block(y, "GET", "/api/age",
        "Calculates the precise age from a given birth date to today.",
        [
            ("birth_date", "Required", "Birth date in DD/MM/YYYY format"),
            ("calendar", "Optional", "System of the input date: 'gregorian' (default) or 'ethiopian'"),
        ],
        f"{BASE}/api/age?birth_date=10/08/2018&calendar=ethiopian&key=YOUR_KEY",
        "If no calendar is specified, Gregorian is assumed."
    )

    s += rect(0, 0, 595, 22, *DB)
    s += text(240, 7, "Page 3 of 4  |  Pagume API", 9, *WH)
    return s


def page5_schemas():
    """Page 5: JSON Schemas, Errors & Support"""
    s = ""
    s += rect(0, 800, 595, 42, *BL)
    s += text(20, 813, "PAGUME BOT API  |  Developer Guide  |  v1.0", 11, *WH, bold=True)

    s += text(50, 762, "JSON Schemas, Error Codes & Support", 20, *DB, bold=True)
    s += rect(50, 754, 245, 3, *BL)

    # Success Schema
    s += rect(50, 720, 235, 22, *DB)
    s += text(57, 729, "Success Response Schema", 12, *WH, bold=True)

    s += rect(50, 640, 235, 76, 0.10, 0.13, 0.18)
    for i, l in enumerate([
        '{  "success": true,',
        '   "data": {',
        '     "day": 13, "month": 8,',
        '     "year": 2018,',
        '     "formatted": "13 - 8 - 2018 ..."',
        '   },',
        '   "meta": {"timestamp": "ISO-8601"} }',
    ]):
        s += text(58, 700 - i*13, l, 9, 0.5, 1.0, 0.6)

    # Error Schema
    s += rect(305, 720, 240, 22, 0.7, 0.1, 0.1)
    s += text(312, 729, "Error Response Schema", 12, *WH, bold=True)

    s += rect(305, 640, 240, 76, 0.10, 0.13, 0.18)
    for i, l in enumerate([
        '{  "success": false,',
        '   "error": {',
        '     "code": "INVALID_PARAMS",',
        '     "message": "date is required."',
        '   }',
        '}',
    ]):
        s += text(313, 700 - i*13, l, 9, 1.0, 0.5, 0.5)

    # Error Codes Table
    s += rect(50, 605, 495, 24, *DB)
    s += text(57, 614, "Common Error Codes", 13, *WH, bold=True)

    errors = [
        ("UNAUTHORIZED",       "401", "API key is missing or invalid."),
        ("RATE_LIMIT_EXCEEDED","429", "Exceeded 30 requests per minute. Slow down."),
        ("INVALID_PARAMS",     "400", "A required parameter is missing or misnamed."),
        ("INVALID_DATE_FORMAT","400", "Date must be in DD/MM/YYYY format."),
        ("VALIDATION_ERROR",   "400", "Date values are out of valid range."),
        ("SERVER_ERROR",       "500", "An internal server error occurred. Contact support."),
    ]
    y = 590
    s += rect(50, y-4, 495, 18, *LB)
    s += text(55, y+2, "Code", 10, *DB, bold=True)
    s += text(200, y+2, "HTTP", 10, *DB, bold=True)
    s += text(250, y+2, "Meaning", 10, *DB, bold=True)
    y -= 18
    for code, http, meaning in errors:
        s += text(55, y+2, code, 9, *BL, bold=True)
        s += text(200, y+2, http, 9, *DB)
        s += text(250, y+2, meaning, 9, *DB)
        y -= 16

    # Support Box
    s += rect(50, 140, 495, 110, *DB)
    s += rect(50, 218, 495, 32, *BL)
    s += text(57, 228, "Need Help? We are here for you.", 14, *WH, bold=True)
    support_lines = [
        "For bug reports, feature requests, and enterprise quota upgrades:",
        "  Email: support@pagumebot.com",
        "  Telegram Bot: Use the 'Contact Admin' button inside Pagume Bot",
        "  Developer Portal: https://ethio-calendar-bot.onrender.com",
        "Stay tuned for v2.0 with batch conversion and lunar calendar support!",
    ]
    y = 200
    for l in support_lines:
        s += text(60, y, l, 10, 0.85, 0.93, 1.0)
        y -= 18

    s += rect(0, 0, 595, 22, *DB)
    s += text(240, 7, "Page 4 of 4  |  Pagume API", 9, *WH)
    return s


if __name__ == "__main__":
    pages = [
        page1_cover(),
        page2_overview(),
        page3_auth(),
        page4_endpoints(),
        page5_schemas(),
    ]
    pdf = finalize_pdf(pages)
    out = "assets/api_guide.pdf"
    with open(out, "wb") as f:
        f.write(pdf)
    print(f"Professional 5-page PDF generated: {out} ({len(pdf):,} bytes)")

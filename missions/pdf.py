"""Server-side PDF rendering of the Bytee Celestial Body Certificate of Exploration (landscape A4)."""
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


def latin1_safe(text):
    try:
        text.encode('latin-1')
        return True
    except UnicodeEncodeError:
        return False


def certificate_pdf(cert):
    buf = BytesIO()
    w, h = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(w, h))

    body = (cert.body_name or 'Celestial').upper()
    c.setTitle(f'Bytee {body} Certificate of Exploration {cert.code}')

    # Deep space dark background
    c.setFillColor(HexColor('#050a18'))
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Accent color based on body
    accent_color = '#ff6b3d' if body == 'MARS' else '#38e1ff'

    # Outer decorative cyan/mars border
    c.setStrokeColor(HexColor(accent_color))
    c.setLineWidth(3)
    c.rect(24, 24, w - 48, h - 48, fill=0)

    # Inner subtle grid frame
    c.setStrokeColor(HexColor('#1d3a6b'))
    c.setLineWidth(1)
    c.rect(34, 34, w - 68, h - 68, fill=0)

    def center(text, y, size, color, font='Helvetica'):
        c.setFillColor(HexColor(color))
        c.setFont(font, size)
        c.drawCentredString(w / 2, y, text)

    center('BYTEE EXPLORER HUB', h - 95, 14, accent_color, 'Helvetica-Bold')
    center(f'{body} CERTIFICATE OF EXPLORATION', h - 145, 30, '#ffffff', 'Helvetica-Bold')
    center('This certifies that', h - 195, 14, '#c9d6ea')

    recipient = cert.recipient_name if latin1_safe(cert.recipient_name) else 'Commander'
    center(recipient, h - 250, 36, '#3dff9a', 'Helvetica-Bold')

    achievement_text = f"has successfully passed 100% full-mark evaluations across all {body.capitalize()} missions"
    center(achievement_text, h - 295, 14, '#c9d6ea')
    center('and is officially certified as an Autonomous Deep Space Explorer.', h - 318, 13, '#c9d6ea')

    center('OFFICIAL SCORE: 100% · FULL CERTIFICATION', h - 365, 15, '#f4f8ff', 'Helvetica-Bold')
    center(f'Issued {cert.issued_at:%d %B %Y}   |   Verification Code: {cert.code}', 65, 11, '#8ea8cb')

    c.showPage()
    c.save()
    return buf.getvalue()

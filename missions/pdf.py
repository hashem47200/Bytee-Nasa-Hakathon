"""Server-side PDF rendering of the NASA Explorer Certificate (landscape A4)."""
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
    c.setTitle(f'NASA Explorer Certificate {cert.code}')
    c.setFillColor(HexColor('#050a18')); c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setStrokeColor(HexColor('#38e1ff')); c.setLineWidth(3); c.rect(24, 24, w - 48, h - 48, fill=0)
    c.setStrokeColor(HexColor('#1d3a6b')); c.setLineWidth(1); c.rect(34, 34, w - 68, h - 68, fill=0)

    def center(text, y, size, color, font='Helvetica'):
        c.setFillColor(HexColor(color)); c.setFont(font, size); c.drawCentredString(w / 2, y, text)

    center('NASA EXPLORER HUB', h - 100, 14, '#38e1ff', 'Helvetica-Bold')
    center('CERTIFICATE OF EXPLORATION', h - 150, 34, '#ffffff', 'Helvetica-Bold')
    center('This certifies that', h - 200, 14, '#c9d6ea')
    center(cert.recipient_name, h - 255, 38, '#3dff9a', 'Helvetica-Bold')
    center('has passed the Mission Exam for', h - 300, 14, '#c9d6ea')
    center(cert.vehicle.name, h - 340, 24, '#ffffff', 'Helvetica-Bold')
    center(f'with a score of {cert.score_percent}%', h - 375, 16, '#f4f8ff')
    center(f'Issued {cert.issued_at:%d %B %Y}   |   Certificate No. {cert.code}', 70, 11, '#c9d6ea')
    c.showPage(); c.save()
    return buf.getvalue()

import io
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from ..models import PDFTask

from django.contrib.auth.models import User


def generate_pdf(number_of_pdfs):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    # Create a text object
    text_obj = pdf.beginText()
    text_obj.setTextOrigin(inch, inch)
    text_obj.setFont('Helvetica', 14)

    # Add lines of text
    demo_users = User.objects.filter(groups__name='demo')
    lines = []
    for demo_user in demo_users:
        lines.append(str(demo_user))
    lines.append(number_of_pdfs)

    # Loop
    for line in lines:
        text_obj.textLine(str(line))

    # Finish
    pdf.drawText(text_obj)
    pdf.showPage()
    pdf.drawText(text_obj)
    pdf.showPage()
    pdf.save()

    return buffer

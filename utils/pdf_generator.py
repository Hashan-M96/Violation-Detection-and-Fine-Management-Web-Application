from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import os
from datetime import datetime
from utils.db import get_violation_details

desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

def generate_receipt(violation_id):
    receipt_filename = f"receipt_{violation_id}.pdf"
    receipt_path = os.path.join(desktop_path, "receipts", receipt_filename)

    if not os.path.exists(os.path.join(desktop_path, "receipts")):
        os.makedirs(os.path.join(desktop_path, "receipts"))

    violation_details = get_violation_details(violation_id)
    if not violation_details:
        raise ValueError("Violation not found")
    
    payment_method_map = {
        "bank_transfer": "Bank Transfer",
        "online": "Online",
        "cash": "Cash"
    }
    
    payment_method = payment_method_map.get(violation_details.get('payment_method'), 'N/A')
    
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create a PDF document
    doc = SimpleDocTemplate(receipt_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    story = []

    # Font colors
    dark_blue = colors.HexColor("#003366")
    light_grey = colors.HexColor("#F5F5F5")

    # Header style
    header_style = ParagraphStyle(
        'Header',
        fontName='Helvetica-Bold',
        fontSize=30,
        leading=34,
        textColor=dark_blue,
        alignment=0,
        spaceAfter=20
    )
    
    subheader_style = ParagraphStyle(
        'SubHeader',
        fontSize=10,
        leading=12,
        textColor=dark_blue,
        spaceAfter=10
    )
    
    logo_path = 'static/logo/logo.jpeg'
    logo = Image(logo_path, width=1.5 * inch, height=1 * inch)
    logo.hAlign='RIGHT'
    header_table_data = [
        [Paragraph("RECEIPT", header_style), logo]
    ]
    header_table = Table(header_table_data, colWidths=[None, logo._width], hAlign='LEFT')
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(Paragraph("Traffic Violations System.", subheader_style))
    story.append(Paragraph("123 ABC xyz lane<br/>Sri Lanka, SL 10000", subheader_style))
    story.append(Spacer(1, 20))

    # Receipt details
    details_data = [
        ["Receipt #", violation_id],
        ["Receipt Date", current_datetime],
    ]

    details_table = Table(details_data, hAlign='LEFT', colWidths=[100, 200])
    details_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, -1), light_grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))

    story.append(details_table)
    story.append(Spacer(1, 10))

    # Violation Details
    item_data = [
        ["Vehicle Number", violation_details['vehicle_number']],
        ["Violation Type", violation_details['violation_type']],
        ["Fine Issued By", violation_details['officer_id']],
        ["Fine Issued Date", violation_details['timestamp']],
        ["Fine Amount", f"LKR {violation_details['fine_amount']:.2f}"],
        ["Payment Method", payment_method],
        ["Status", violation_details['status']],
    ]

    item_table = Table(item_data, hAlign='LEFT', colWidths=[150, 300])
    item_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BACKGROUND', (0, 0), (-1, -1), light_grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))

    story.append(item_table)
    story.append(Spacer(1, 30))

    # Thank you message
    thank_you_style = ParagraphStyle(
        'ThankYou',
        fontName='Helvetica-BoldOblique',
        fontSize=16,
        leading=18,
        spaceBefore=30,
        alignment=1,
        textColor=dark_blue
    )

    story.append(Paragraph("Thank You For Your Payment!", thank_you_style))

    doc.build(story)

    return receipt_path
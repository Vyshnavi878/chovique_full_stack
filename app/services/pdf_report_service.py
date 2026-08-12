import io
from typing import Any
from datetime import datetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#555555"))
        page_text = f"Page {self._pageNumber} of {page_count}"
        
        # Draw header (except page 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "CHOVIQUE LUXURY CHOCOLATES — BUSINESS REPORT")
            self.setStrokeColor(colors.HexColor("#c9a84c"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)

        # Draw footer
        self.drawRightString(558, 40, page_text)
        self.drawString(54, 40, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.restoreState()


class LandscapeNumberedCanvas(NumberedCanvas):
    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#555555"))
        page_text = f"Page {self._pageNumber} of {page_count}"
        
        # Draw header (except page 1)
        if self._pageNumber > 1:
            self.drawString(54, 550, "CHOVIQUE LUXURY CHOCOLATES — BUSINESS REPORT")
            self.setStrokeColor(colors.HexColor("#c9a84c"))
            self.setLineWidth(0.5)
            self.line(54, 542, 738, 542)

        # Draw footer
        self.drawRightString(738, 30, page_text)
        self.drawString(54, 30, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.restoreState()


class PdfReportService:

    @staticmethod
    def _create_styles():
        styles = getSampleStyleSheet()
        
        # Custom luxury styles
        title_style = ParagraphStyle(
            'LuxuryTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1a1512"),
            spaceAfter=6
        )
        
        meta_style = ParagraphStyle(
            'LuxuryMeta',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=10,
            textColor=colors.HexColor("#555555"),
            spaceAfter=15
        )
        
        section_style = ParagraphStyle(
            'LuxurySection',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#c9a84c"),
            spaceBefore=12,
            spaceAfter=8
        )

        cell_style = ParagraphStyle(
            'LuxuryCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1a1512")
        )

        header_style = ParagraphStyle(
            'LuxuryHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11,
            textColor=colors.white
        )

        return title_style, meta_style, section_style, cell_style, header_style

    @classmethod
    def generate_customer_report(cls, start_date: str, end_date: str, kpis: list, customers: list) -> io.BytesIO:
        out = io.BytesIO()
        doc = SimpleDocTemplate(
            out,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        title_style, meta_style, section_style, cell_style, header_style = cls._create_styles()
        story = []

        # Document Header
        story.append(Paragraph("CHOVIQUE LUXURY CHOCOLATES — CUSTOMERS REPORT", title_style))
        story.append(Paragraph(f"Date Range: {start_date} to {end_date}", meta_style))
        story.append(Spacer(1, 10))

        # KPI Summary Table
        story.append(Paragraph("KPI SUMMARY", section_style))
        kpi_data = [
            [Paragraph(f"<b>{kpi.title}</b>", cell_style) for kpi in kpis],
            [Paragraph(f"<font color='#c9a84c'><b>{kpi.value}</b></font>", ParagraphStyle('KPIVal', parent=cell_style, fontSize=11, leading=13)) for kpi in kpis]
        ]
        
        kpi_table = Table(kpi_data, colWidths=[100]*len(kpis))
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#fbf9f6")),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#dcdcdc")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 20))

        # Detailed Table
        story.append(Paragraph("DETAILED CUSTOMER DATA", section_style))
        
        table_data = [[
            Paragraph("Customer Name", header_style),
            Paragraph("Email", header_style),
            Paragraph("Phone", header_style),
            Paragraph("Orders", header_style),
            Paragraph("Total Spend", header_style),
            Paragraph("Joined Date", header_style)
        ]]

        for c in customers:
            table_data.append([
                Paragraph(str(c[0]), cell_style),
                Paragraph(str(c[1]), cell_style),
                Paragraph(str(c[2]), cell_style),
                Paragraph(str(c[3]), cell_style),
                Paragraph(str(c[4]), cell_style),
                Paragraph(str(c[5]), cell_style)
            ])

        # Width config
        col_widths = [110, 130, 80, 50, 70, 64]
        
        det_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        det_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1a1512")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f9f9f9")]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e2e2")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(det_table)

        doc.build(story, canvasmaker=NumberedCanvas)
        out.seek(0)
        return out

    @classmethod
    def generate_orders_report(cls, start_date: str, end_date: str, orders: list) -> io.BytesIO:
        out = io.BytesIO()
        # Orders has 12 columns, use Landscape for neat printable view
        doc = SimpleDocTemplate(
            out,
            pagesize=landscape(letter),
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        title_style, meta_style, section_style, cell_style, header_style = cls._create_styles()
        story = []

        story.append(Paragraph("CHOVIQUE LUXURY CHOCOLATES — ORDERS REPORT", title_style))
        story.append(Paragraph(f"Date Range: {start_date} to {end_date}", meta_style))
        story.append(Spacer(1, 10))

        story.append(Paragraph("DETAILED ORDERS DATA", section_style))

        headers = [
            "Order ID", "Customer", "Email", "Date", "Items",
            "Subtotal", "Discount", "Shipping", "Tax", "Total", "Payment", "Status"
        ]
        
        table_data = [[Paragraph(h, header_style) for h in headers]]

        for o in orders:
            table_data.append([
                Paragraph(str(o[0]), cell_style),
                Paragraph(str(o[1]), cell_style),
                Paragraph(str(o[2]), cell_style),
                Paragraph(str(o[3]), cell_style),
                Paragraph(str(o[4]), cell_style),
                Paragraph(str(o[5]), cell_style),
                Paragraph(str(o[6]), cell_style),
                Paragraph(str(o[7]), cell_style),
                Paragraph(str(o[8]), cell_style),
                Paragraph(str(o[9]), cell_style),
                Paragraph(str(o[10]), cell_style),
                Paragraph(str(o[11]), cell_style)
            ])

        # Landscape width totals to 684pt width
        col_widths = [80, 75, 85, 65, 30, 45, 45, 45, 40, 50, 60, 64]
        
        det_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        det_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1a1512")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f9f9f9")]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e2e2")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(det_table)

        doc.build(story, canvasmaker=LandscapeNumberedCanvas)
        out.seek(0)
        return out

    @classmethod
    def generate_analytics_report(cls, start_date: str, end_date: str, summary_data: dict) -> io.BytesIO:
        out = io.BytesIO()
        doc = SimpleDocTemplate(
            out,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        title_style, meta_style, section_style, cell_style, header_style = cls._create_styles()
        story = []

        story.append(Paragraph("CHOVIQUE LUXURY CHOCOLATES — PERFORMANCE REPORT", title_style))
        story.append(Paragraph(f"Date Range: {start_date} to {end_date}", meta_style))
        story.append(Spacer(1, 10))

        story.append(Paragraph("METRICS SUMMARY", section_style))

        metrics = [
            ("Total Revenue", f"₹{summary_data.get('total_revenue', 0.0):,.2f}"),
            ("Total Orders", f"{summary_data.get('total_orders', 0):,}"),
            ("Total Customers", f"{summary_data.get('total_customers', 0):,}"),
            ("New Customers", f"{summary_data.get('new_customers', 0):,}"),
            ("Repeat Customers", f"{summary_data.get('repeat_customers', 0):,}"),
            ("Average Order Value", f"₹{summary_data.get('avg_order_value', 0.0):,.2f}"),
            ("Total Products Sold", f"{summary_data.get('total_products_sold', 0):,}"),
            ("Total Discounts", f"₹{summary_data.get('total_discounts', 0.0):,.2f}"),
            ("Total Tax", f"₹{summary_data.get('total_tax', 0.0):,.2f}"),
            ("Total Shipping Revenue", f"₹{summary_data.get('total_shipping_revenue', 0.0):,.2f}"),
        ]

        table_data = [[
            Paragraph("Metric Key", header_style),
            Paragraph("Metric Value", header_style)
        ]]

        for key, val in metrics:
            table_data.append([
                Paragraph(key, cell_style),
                Paragraph(f"<b>{val}</b>", cell_style)
            ])

        det_table = Table(table_data, colWidths=[250, 254])
        det_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1a1512")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f9f9f9")]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e2e2")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(det_table)

        doc.build(story, canvasmaker=NumberedCanvas)
        out.seek(0)
        return out

    @classmethod
    def generate_invoice_pdf(cls, order: Any, user_name: str, user_email: str) -> io.BytesIO:
        out = io.BytesIO()
        doc = SimpleDocTemplate(
            out,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'InvBrandTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#120e0b")
        )
        right_title_style = ParagraphStyle(
            'InvRightTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            alignment=2,
            textColor=colors.HexColor("#120e0b")
        )
        body_style = ParagraphStyle(
            'InvBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=12,
            textColor=colors.HexColor("#333333")
        )
        header_cell_style = ParagraphStyle(
            'InvHeaderCell',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#f5efe6")
        )
        item_cell_style = ParagraphStyle(
            'InvItemCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#222222")
        )

        story = []

        # Header Table (Brand Left, Invoice Info Right)
        brand_p = Paragraph("CHOVIQUE", title_style)
        brand_sub_p = Paragraph("PREMIUM HANDMADE CHOCOLATES<br/><font size=7 color='#666666'>Chovique Chocolates Pvt. Ltd.<br/>123, Chocolate Lane, Hitec City, Hyderabad, Telangana - 500081<br/>Email: hello@chovique.com | Phone: +91 98765 43210<br/>GSTIN: 36ABCDE1234F1ZS</font>", body_style)

        inv_title_p = Paragraph("INVOICE", right_title_style)
        
        created_str = order.created_at.strftime('%d %b %Y') if getattr(order, 'created_at', None) else datetime.now().strftime('%d %b %Y')
        payment_method = getattr(order, 'payment_method', 'Cash on Delivery') or 'Cash on Delivery'
        status_val = getattr(order, 'status', 'Confirmed') or 'Confirmed'
        p_status = getattr(order, 'payment_status', 'Paid') or ('Paid' if status_val != 'Cancelled' else 'Cancelled')

        inv_details_text = f"<b>Invoice No:</b> INV-{order.id}<br/><b>Order No:</b> {order.id}<br/><b>Invoice Date:</b> {created_str}<br/><b>Payment Method:</b> {payment_method}<br/><b>Payment Status:</b> {p_status}<br/><b>Order Status:</b> {status_val}"
        inv_details_p = Paragraph(inv_details_text, ParagraphStyle('InvRightText', parent=body_style, alignment=2))

        header_table = Table(
            [[[brand_p, brand_sub_p], [inv_title_p, inv_details_p]]],
            colWidths=[290, 250]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 12))

        # Bill To / Ship To Table
        shipping_address = getattr(order, 'shipping_address', {}) or {}
        bill_to_text = f"<b>BILL TO:</b><br/>{shipping_address.get('name', user_name)}<br/>{user_email}<br/>{shipping_address.get('phone', '9876543210')}"
        ship_to_text = f"<b>SHIP TO:</b><br/>{shipping_address.get('name', user_name)}<br/>{shipping_address.get('street', '')}<br/>{shipping_address.get('city', '')}, {shipping_address.get('state', '')} - {shipping_address.get('zip', shipping_address.get('zip_code', ''))}<br/>India<br/>{shipping_address.get('phone', '9876543210')}"

        address_table = Table(
            [[Paragraph(bill_to_text, body_style), Paragraph(ship_to_text, body_style)]],
            colWidths=[270, 270]
        )
        address_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#fcfbfa")),
            ('PADDING', (0,0), (-1,-1), 8),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#e5dccb")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(address_table)
        story.append(Spacer(1, 12))

        # Products Table
        table_headers = ["#", "PRODUCT", "SKU", "QTY", "UNIT PRICE", "DISCOUNT", "TOTAL"]
        items_data = [[Paragraph(h, header_cell_style) for h in table_headers]]

        items_list = getattr(order, "items", []) or []
        for idx, item in enumerate(items_list, 1):
            prod_obj = getattr(item, 'product', None)
            prod_name = prod_obj.name if prod_obj else "Chovique Product"
            sku = getattr(prod_obj, 'sku', None) or f"SCB-250G"
            qty = item.quantity or 1
            unit_price = item.price or 0.0
            item_disc = 0.0
            line_tot = (unit_price * qty) - item_disc

            items_data.append([
                Paragraph(str(idx), item_cell_style),
                Paragraph(prod_name, item_cell_style),
                Paragraph(str(sku), item_cell_style),
                Paragraph(str(qty), item_cell_style),
                Paragraph(f"₹{unit_price:,.2f}", item_cell_style),
                Paragraph(f"₹{item_disc:,.2f}", item_cell_style),
                Paragraph(f"₹{line_tot:,.2f}", item_cell_style),
            ])

        prod_table = Table(items_data, colWidths=[20, 185, 80, 35, 75, 65, 80])
        prod_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#120e0b")),
            ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e5dccb")),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(prod_table)
        story.append(Spacer(1, 12))

        # Summary Table
        coupon_disc = getattr(order, 'coupon_discount', 0.0) or 0.0
        shipping_val = getattr(order, 'shipping', 0.0) or 0.0
        subtotal_val = getattr(order, 'subtotal', 0.0) or 0.0
        grand_total = getattr(order, 'total', 0.0) or 0.0

        summary_rows = [
            ("Subtotal:", f"₹{subtotal_val:,.2f}"),
            ("Coupon Discount:", f"-₹{coupon_disc:,.2f}" if coupon_disc > 0 else "₹0.00"),
            ("Shipping:", f"₹{shipping_val:,.2f}"),
            ("Grand Total:", f"₹{grand_total:,.2f} ({p_status})"),
        ]

        summary_table_data = []
        for label, val in summary_rows:
            is_total = label == "Grand Total:"
            lbl_style = ParagraphStyle('SumLbl', parent=body_style, fontName='Helvetica-Bold' if is_total else 'Helvetica', fontSize=10 if is_total else 8.5, alignment=2)
            val_style = ParagraphStyle('SumVal', parent=body_style, fontName='Helvetica-Bold' if is_total else 'Helvetica', fontSize=10 if is_total else 8.5, alignment=2, textColor=colors.HexColor("#2ecc71") if is_total and p_status == "Paid" else colors.HexColor("#120e0b"))
            summary_table_data.append(["", Paragraph(label, lbl_style), Paragraph(val, val_style)])

        summary_table = Table(summary_table_data, colWidths=[300, 120, 120])
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 3),
            ('LINEABOVE', (1,3), (2,3), 1, colors.HexColor("#120e0b")),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Footer Note
        footer_p = Paragraph("Thank you for choosing CHOVIQUE. We appreciate your trust and support.<br/><font size=7 color='#888888'>This is a computer generated invoice and does not require a signature.</font>", ParagraphStyle('InvFootText', parent=body_style, alignment=1))
        story.append(footer_p)

        doc.build(story)
        out.seek(0)
        return out


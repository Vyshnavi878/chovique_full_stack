import io
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

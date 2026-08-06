import datetime
from app.models.order import Order

class InvoiceService:
    @staticmethod
    def generate_html_invoice(order: Order, user_name: str, user_email: str) -> str:
        items_html = ""
        for item in order.items:
            product_name = item.product.name if item.product else "Unknown Product"
            items_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{product_name}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">{item.quantity}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">₹{item.price:.2f}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">₹{item.price * item.quantity:.2f}</td>
            </tr>
            """
            
        shipping_address = order.shipping_address or {}
        address_html = f"""
        {shipping_address.get('street', '')}<br>
        {shipping_address.get('city', '')}, {shipping_address.get('state', '')} {shipping_address.get('zip_code', '')}<br>
        {shipping_address.get('country', 'India')}
        """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Invoice - {order.id}</title>
            <style>
                body {{
                    font-family: 'Helvetica Neue', 'Helvetica', Helvetica, Arial, sans-serif;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f9f9f9;
                }}
                .invoice-box {{
                    max-width: 800px;
                    margin: 40px auto;
                    padding: 30px;
                    border: 1px solid #eee;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.15);
                    background-color: #fff;
                    font-size: 16px;
                    line-height: 24px;
                }}
                table {{
                    width: 100%;
                    line-height: inherit;
                    text-align: left;
                    border-collapse: collapse;
                }}
                table td {{
                    padding: 5px;
                    vertical-align: top;
                }}
                .header-row td {{
                    padding-bottom: 20px;
                }}
                .title {{
                    font-size: 45px;
                    line-height: 45px;
                    color: #d4af37; /* Gold */
                    font-weight: bold;
                }}
                .info-table {{
                    margin-bottom: 40px;
                }}
                .items-table th {{
                    background: #f3f3f3;
                    border-bottom: 1px solid #ddd;
                    font-weight: bold;
                    padding: 10px;
                }}
                .totals-row td {{
                    border-top: 2px solid #eee;
                    font-weight: bold;
                }}
                @media print {{
                    body {{
                        background-color: #fff;
                    }}
                    .invoice-box {{
                        box-shadow: none;
                        border: none;
                        margin: 0;
                        padding: 0;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="invoice-box">
                <table class="info-table">
                    <tr class="header-row">
                        <td class="title">Chovique</td>
                        <td style="text-align: right;">
                            Invoice #: {order.id[:8].upper()}<br>
                            Created: {order.created_at.strftime('%b %d, %Y') if order.created_at else datetime.date.today().strftime('%b %d, %Y')}<br>
                            Status: {order.status.upper()}
                        </td>
                    </tr>
                </table>
                
                <table class="info-table">
                    <tr>
                        <td>
                            <strong>Bill To:</strong><br>
                            {user_name}<br>
                            {user_email}<br>
                        </td>
                        <td style="text-align: right;">
                            <strong>Ship To:</strong><br>
                            {address_html}
                        </td>
                    </tr>
                </table>
                
                <table class="items-table">
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th style="text-align: center;">Qty</th>
                            <th style="text-align: right;">Price</th>
                            <th style="text-align: right;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                        
                        <tr class="totals-row">
                            <td colspan="3" style="text-align: right; padding: 10px;">Subtotal</td>
                            <td style="text-align: right; padding: 10px;">₹{order.subtotal:.2f}</td>
                        </tr>
                        <tr>
                            <td colspan="3" style="text-align: right; padding: 10px;">Discount</td>
                            <td style="text-align: right; padding: 10px; color: red;">-₹{order.discount:.2f}</td>
                        </tr>
                        <tr>
                            <td colspan="3" style="text-align: right; padding: 10px;">Shipping</td>
                            <td style="text-align: right; padding: 10px;">₹{order.shipping:.2f}</td>
                        </tr>
                        <tr>
                            <td colspan="3" style="text-align: right; padding: 10px;">GST (5%)</td>
                            <td style="text-align: right; padding: 10px;">₹{order.tax:.2f}</td>
                        </tr>
                        <tr style="font-size: 1.2em;">
                            <td colspan="3" style="text-align: right; padding: 10px; border-top: 2px solid #333;"><strong>Total</strong></td>
                            <td style="text-align: right; padding: 10px; border-top: 2px solid #333;"><strong>₹{order.total:.2f}</strong></td>
                        </tr>
                    </tbody>
                </table>
                
                <div style="text-align: center; margin-top: 50px; color: #777; font-size: 14px;">
                    Thank you for indulging with Chovique Chocolatier!<br>
                    <a href="javascript:window.print()" style="color: #d4af37; text-decoration: none; display: inline-block; margin-top: 10px; padding: 10px 20px; border: 1px solid #d4af37; border-radius: 5px;" class="no-print">Print / Save as PDF</a>
                </div>
            </div>
            <style>
                @media print {{
                    .no-print {{
                        display: none !important;
                    }}
                }}
            </style>
        </body>
        </html>
        """
        return html

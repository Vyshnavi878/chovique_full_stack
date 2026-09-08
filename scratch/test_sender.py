import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

# Load credentials from environment variables (set in .env or shell before running)
server = os.environ.get('MAIL_SERVER', 'smtp-relay.brevo.com')
port = int(os.environ.get('MAIL_PORT', '587'))
user = os.environ.get('MAIL_USERNAME', '')
pwd = os.environ.get('MAIL_PASSWORD', '')
mail_from = os.environ.get('MAIL_FROM', 'chovique25@gmail.com')

if not user or not pwd:
    raise RuntimeError(
        'Set MAIL_USERNAME and MAIL_PASSWORD env variables before running this script.\n'
        'e.g.  $env:MAIL_USERNAME="your_smtp_user"  $env:MAIL_PASSWORD="your_smtp_key"'
    )

msg = MIMEMultipart('alternative')
msg['Subject'] = 'Chovique Chocolatier Header Test'
msg['From'] = formataddr(('Chovique Chocolatier', mail_from))
msg['Reply-To'] = formataddr(('Chovique Concierge', mail_from))
msg['To'] = mail_from

msg.attach(MIMEText('<b>Testing header</b>', 'html'))

with smtplib.SMTP(server, port, timeout=10) as s:
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(user, pwd)
    resp = s.send_message(msg)
    print('SEND RESULT:', resp)

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import os
from datetime import datetime

class EmailNotifier:
    def __init__(self, smtp_host: str = None, smtp_port: int = None, 
                 smtp_user: str = None, smtp_password: str = None):
        # Use environment variables or provided values
        self.smtp_host = smtp_host or os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = smtp_user or os.getenv('SMTP_USER', '')
        self.smtp_password = smtp_password or os.getenv('SMTP_PASSWORD', '')
        
    def send_availability_notification(self, recipients: List[str], item_name: str, 
                                     item_url: str, is_available: bool):
        """Send email notification about availability change"""
        if not recipients or not self.smtp_user:
            print("Email notification skipped: No recipients or SMTP not configured")
            return False
        
        subject = f"Stock Alert: {item_name} is now {'AVAILABLE' if is_available else 'OUT OF STOCK'}"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; border-radius: 10px;">
                    <h2 style="color: {'#27ae60' if is_available else '#e74c3c'};">
                        Stock Status Update
                    </h2>
                    <p style="font-size: 16px;">
                        <strong>{item_name}</strong> is now 
                        <span style="color: {'#27ae60' if is_available else '#e74c3c'}; font-weight: bold;">
                            {'AVAILABLE' if is_available else 'OUT OF STOCK'}
                        </span>
                    </p>
                    <p>
                        <a href="{item_url}" style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                            View Item
                        </a>
                    </p>
                    <hr style="border: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #666; font-size: 12px;">
                        Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
            </body>
        </html>
        """
        
        plain_body = f"""
        Stock Status Update
        
        {item_name} is now {'AVAILABLE' if is_available else 'OUT OF STOCK'}
        
        View item: {item_url}
        
        Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = ', '.join(recipients)
            
            # Attach parts
            msg.attach(MIMEText(plain_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"Email sent successfully to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            return False 
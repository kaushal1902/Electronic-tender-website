"""
Utility functions for the TenderVista.
Contains helper functions for email sending, token generation, and data processing.
`"""

import os
import random
import string
import json
from datetime import datetime, timedelta
from functools import wraps

from flask import flash, redirect, url_for, current_app
from flask_login import current_user
from flask_mail import Message

from app import mail, app

# Load email settings from the JSON file
def load_email_settings():
    """Load email settings from JSON file"""
    try:
        if os.path.exists('instance/email_settings.json'):
            with open('instance/email_settings.json', 'r') as f:
                settings = json.load(f)
                return settings
        return {}
    except Exception as e:
        app.logger.error(f"Error loading email settings: {str(e)}")
        return {}

# Initialize email settings from the file
settings = load_email_settings()
for key, value in settings.items():
    app.config[key] = value

def admin_required(f):
    """Decorator to restrict access to admin users only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))

        # Check if user has admin role
        if not hasattr(current_user, 'roles') or 'admin' not in [role.name for role in current_user.roles]:
            flash('Access denied. You do not have administrative privileges.', 'danger')
            return redirect(url_for('index'))

        return f(*args, **kwargs)
    return decorated_function

def generate_otp(length=6):
    """Generate a random numeric OTP of specified length"""
    return ''.join(random.choices(string.digits, k=length))

def generate_captcha():
    """Generate a simple captcha string"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def send_email(subject, recipients, body, html=None):
    """Send an email using Flask-Mail"""
    try:
        msg = Message(
            subject=subject,
            recipients=recipients if isinstance(recipients, list) else [recipients],
            body=body,
            html=html
        )
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Error sending email: {str(e)}")
        return False

def send_verification_email(user, otp):
    """Send verification email with OTP"""
    subject = "TenderVista - Email Verification"
    body = f"""
Hello {user.name},

Thank you for registering with the TenderVista.

Your verification code is: {otp}

This code will expire in 15 minutes.

Best regards,
TenderVista Team
    """
    html = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4A6FDC; padding: 15px; color: white; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .code {{ font-size: 24px; font-weight: bold; background-color: #f0f0f0; padding: 10px; 
                margin: 15px 0; text-align: center; letter-spacing: 5px; }}
        .footer {{ font-size: 12px; color: #777; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Email Verification</h2>
        </div>
        <div class="content">
            <p>Hello {user.name},</p>
            <p>Thank you for registering with the TenderVista.</p>
            <p>Your verification code is:</p>
            <div class="code">{otp}</div>
            <p>This code will expire in 15 minutes.</p>
            <p>Best regards,<br>TenderVista Team</p>
        </div>
        <div class="footer">
            &copy; {datetime.now().year} TenderVista. All rights reserved.
        </div>
    </div>
</body>
</html>
    """
    return send_email(subject, user.email, body, html)

def send_tender_winner_notification(application):
    """Send email notification to the winner of a tender"""
    subject = f"Congratulations! You've won the tender: {application.tender.title}"
    body = f"""
Hello {application.user.name},

🎊 Congratulations! 🎊

Your application for the tender "{application.tender.title}" has been selected as the winner!

Tender Details:
- Title: {application.tender.title}
- Budget: ₹{application.tender.budget:,.2f}
- Your Quote: ₹{application.price_quote:,.2f}
- Completion Time: {application.completion_time} days
- Final Score: {application.bid_score}/100

This is a great achievement and we look forward to working with you. Please log in to your account to view the complete details and next steps for contract finalization.

Best regards,
TenderVista Team
"""
    html = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #28a745; padding: 15px; color: white; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .tender-details {{ background-color: #f0f0f0; padding: 15px; margin: 15px 0; }}
        .score {{ color: #28a745; font-weight: bold; }}
        .footer {{ font-size: 12px; color: #777; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🏆 Tender Winner Notification</h2>
        </div>
        <div class="content">
            <p>Hello {application.user.name},</p>
            <p><strong>Congratulations!</strong> Your application for the tender "{application.tender.title}" has been selected as the winner.</p>

            <div class="tender-details">
                <h3>Tender Details:</h3>
                <p><strong>Title:</strong> {application.tender.title}</p>
                <p><strong>Budget:</strong> ₹{application.tender.budget:,.2f}</p>
                <p><strong>Your Quote:</strong> ₹{application.price_quote:,.2f}</p>
                <p><strong>Completion Time:</strong> {application.completion_time} days</p>
                <p><strong>Final Score:</strong> <span class="score">{application.bid_score}/100</span></p>
            </div>

            <p>Please log in to your account to view the complete details and next steps.</p>
            <p>Best regards,<br>TenderVista Team</p>
        </div>
        <div class="footer">
            &copy; {datetime.now().year} TenderVista. All rights reserved.
        </div>
    </div>
</body>
</html>
    """
    return send_email(subject, application.user.email, body, html)

def send_tender_result_notification(application, winner):
    """Send email notification to other applicants about tender results"""
    subject = f"Tender Result Announcement: {application.tender.title}"
    body = f"""
Hello {application.user.name},

We would like to inform you that the tender "{application.tender.title}" has been awarded.

The winning bid was submitted by {winner.user.company_name}.

Thank you for your participation in this tender. We encourage you to continue applying for future opportunities.

Tender Details:
- Title: {application.tender.title}
- Your Bid Score: {application.bid_score}/100
- Your Ranking: {application.ranking}

We appreciate your interest and participation in our tender process.

Best regards,
TenderVista Team
"""
    return send_email(subject, application.user.email, body)

def send_new_tender_notification(tender, user):
    """Send notification about a new tender to a potential supplier"""
    subject = f"New Tender Alert: {tender.title}"
    body = f"""
Hello {user.name},

A new tender matching your industry sector has been posted:

Tender Details:
- Title: {tender.title}
- Category: {tender.category.replace('_', ' ').title()}
- Budget: ₹{tender.budget:,.2f}
- Submission Deadline: {tender.submission_deadline.strftime('%Y-%m-%d %H:%M')}

Description:
{tender.description[:200]}...

Log in to your account to view the full details and submit your application.

Best regards,
TenderVista Team
    """
    html = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4A6FDC; padding: 15px; color: white; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .tender-details {{ background-color: #f0f0f0; padding: 15px; margin: 15px 0; }}
        .deadline {{ color: #dc3545; font-weight: bold; }}
        .cta-button {{ display: inline-block; background-color: #4A6FDC; color: white; 
                       padding: 10px 20px; text-decoration: none; border-radius: 4px; }}
        .footer {{ font-size: 12px; color: #777; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>📢 New Tender Alert</h2>
        </div>
        <div class="content">
            <p>Hello {user.name},</p>
            <p>A new tender matching your industry sector has been posted:</p>

            <div class="tender-details">
                <h3>Tender Details:</h3>
                <p><strong>Title:</strong> {tender.title}</p>
                <p><strong>Category:</strong> {tender.category.replace('_', ' ').title()}</p>
                <p><strong>Budget:</strong> ₹{tender.budget:,.2f}</p>
                <p><strong>Submission Deadline:</strong> <span class="deadline">{tender.submission_deadline.strftime('%Y-%m-%d %H:%M')}</span></p>
                <p><strong>Description:</strong><br>{tender.description[:200]}...</p>
            </div>

            <p>Log in to your account to view the full details and submit your application.</p>
            <a href="{url_for('tender_details', tender_id=tender.id, _external=True)}" class="cta-button">View Tender Details</a>
            <p>Best regards,<br>TenderVista Team</p>
        </div>
        <div class="footer">
            &copy; {datetime.now().year} TenderVista. All rights reserved.
        </div>
    </div>
</body>
</html>
    """
    return send_email(subject, user.email, body, html)

def send_application_status_update(application):
    """Send email notification about application status update"""
    subject = f"Application Status Update: {application.tender.title}"
    status_text = application.status.replace('_', ' ').title()

    body = f"""
Hello {application.user.name},

Congratulations! Your application for the tender "{application.tender.title}" has been selected as the winner.

Tender Details:
- Title: {application.tender.title}
- Budget: ₹{application.tender.budget:,.2f}
- Your Quote: ₹{application.price_quote:,.2f}

Please log in to your account to view the details and next steps.

Best regards,
TenderVista Team
    """
    html = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #28a745; padding: 15px; color: white; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .tender-details {{ background-color: #f0f0f0; padding: 15px; margin: 15px 0; }}
        .footer {{ font-size: 12px; color: #777; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Tender Winner Notification</h2>
        </div>
        <div class="content">
            <p>Hello {application.user.name},</p>
            <p><strong>Congratulations!</strong> Your application for the tender "{application.tender.title}" has been selected as the winner.</p>

            <div class="tender-details">
                <h3>Tender Details:</h3>
                <p><strong>Title:</strong> {application.tender.title}</p>
                <p><strong>Budget:</strong> ₹{application.tender.budget:,.2f}</p>
                <p><strong>Your Quote:</strong> ₹{application.price_quote:,.2f}</p>
            </div>

            <p>Please log in to your account to view the details and next steps.</p>
            <p>Best regards,<br>TenderVista Team</p>
        </div>
        <div class="footer">
            &copy; {datetime.now().year} TenderVista. All rights reserved.
        </div>
    </div>
</body>
</html>
    """
    return send_email(subject, application.user.email, body, html)

def send_application_status_update(application):
    """Send email notification about application status update"""
    subject = f"Application Status Update: {application.tender.title}"
    status_text = application.status.replace('_', ' ').title()

    body = f"""
Hello {application.user.name},

The status of your application for the tender "{application.tender.title}" has been updated to: {status_text}

Tender Details:
- Title: {application.tender.title}
- Budget: ₹{application.tender.budget:,.2f}
- Your Quote: ₹{application.price_quote:,.2f}

Please log in to your account to view more details.

Best regards,
TenderVista Team
    """
    html = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4A6FDC; padding: 15px; color: white; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .status {{ font-size: 18px; font-weight: bold; margin: 15px 0; color: #4A6FDC; }}
        .tender-details {{ background-color: #f0f0f0; padding: 15px; margin: 15px 0; }}
        .footer {{ font-size: 12px; color: #777; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Application Status Update</h2>
        </div>
        <div class="content">
            <p>Hello {application.user.name},</p>
            <p>The status of your application for the tender "{application.tender.title}" has been updated to:</p>
            <div class="status">{status_text}</div>

            <div class="tender-details">
                <h3>Tender Details:</h3>
                <p><strong>Title:</strong> {application.tender.title}</p>
                <p><strong>Budget:</strong> ₹{application.tender.budget:,.2f}</p>
                <p><strong>Your Quote:</strong> ₹{application.price_quote:,.2f}</p>
            </div>

            <p>Please log in to your account to view more details.</p>
            <p>Best regards,<br>TenderVista Team</p>
        </div>
        <div class="footer">
            &copy; {datetime.now().year} TenderVista. All rights reserved.
        </div>
    </div>
</body>
</html>
    """
    return send_email(subject, application.user.email, body, html)

def send_new_tender_notification(tender, recipients):
    """Send notification about a new tender to potential suppliers"""
    subject = f"New Tender Alert: {tender.title}"

    body = f"""
Hello,

A new tender has been posted in your industry sector:

Tender Details:
- Title: {tender.title}
- Category: {tender.category.replace('_', ' ').title()}
- Budget: ₹{tender.budget:,.2f}
- Submission Deadline: {tender.submission_deadline.strftime('%Y-%m-%d %H:%M')}

Log in to your account to view the full details and submit your application.

Best regards,
TenderVista Team
    """
    html = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4A6FDC; padding: 15px; color: white; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .tender-details {{ background-color: #f0f0f0; padding: 15px; margin: 15px 0; }}
        .cta-button {{ display: inline-block; background-color: #4A6FDC; color: white; padding: 10px 20px; 
                       text-decoration: none; border-radius: 4px; margin-top: 15px; }}
        .deadline {{ color: #e74c3c; font-weight: bold; }}
        .footer {{ font-size: 12px; color: #777; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>New Tender Alert</h2>
        </div>
        <div class="content">
            <p>Hello,</p>
            <p>A new tender has been posted in your industry sector:</p>

            <div class="tender-details">
                <h3>Tender Details:</h3>
                <p><strong>Title:</strong> {tender.title}</p>
                <p><strong>Category:</strong> {tender.category.replace('_', ' ').title()}</p>
                <p><strong>Budget:</strong> ₹{tender.budget:,.2f}</p>
                <p><strong>Submission Deadline:</strong> <span class="deadline">{tender.submission_deadline.strftime('%Y-%m-%d %H:%M')}</span></p>
            </div>

            <p>Log in to your account to view the full details and submit your application.</p>
            <a href="{url_for('tender_details', tender_id=tender.id, _external=True)}" class="cta-button">View Tender</a>
            <p>Best regards,<br>TenderVista Team</p>
        </div>
        <div class="footer">
            &copy; {datetime.now().year} TenderVista. All rights reserved.
        </div>
    </div>
</body>
</html>
    """
    return send_email(subject, recipients, body, html)

def format_currency(value):
    """Format a number as currency with ₹ symbol and commas"""
    if value is None:
        return '₹0.00'
    return f'₹{value:,.2f}'

def format_date(date):
    """Format a date to a readable string"""
    if date is None:
        return 'N/A'
    return date.strftime('%b %d, %Y')

def format_datetime(dt):
    """Format a datetime to a readable string with time"""
    if dt is None:
        return 'N/A'
    return dt.strftime('%b %d, %Y, %H:%M')

def get_remaining_time(deadline):
    """Get a string representing the remaining time until the deadline"""
    if deadline is None:
        return 'No deadline'

    now = datetime.now()
    if deadline < now:
        return 'Expired'

    delta = deadline - now
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    if days > 0:
        return f'{days} day{"s" if days != 1 else ""}, {hours} hr{"s" if hours != 1 else ""}'
    elif hours > 0:
        return f'{hours} hour{"s" if hours != 1 else ""}, {minutes} min{"s" if minutes != 1 else ""}'
    else:
        return f'{minutes} minute{"s" if minutes != 1 else ""}'
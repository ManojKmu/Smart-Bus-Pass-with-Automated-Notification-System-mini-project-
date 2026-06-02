"""
Email Configuration - Secure Credential Management
Reads email credentials from environment variables
"""

import os

# ============================================
# EMAIL CONFIGURATION
# ============================================

def get_email_config():
    """
    Get email configuration from environment variables
    Returns dict with email settings
    """
    # Read from environment variables
    email_user = os.environ.get('EMAIL_USER')
    email_password = os.environ.get('EMAIL_PASSWORD')
    
    # Fallback to default if not set (for development only)
    if not email_user:
        email_user = 'your_email@gmail.com'  # Change this
        print("⚠️  WARNING: EMAIL_USER not set in environment variables")
    
    if not email_password:
        email_password = 'your_app_password'  # Change this
        print("⚠️  WARNING: EMAIL_PASSWORD not set in environment variables")
    
    return {
        'user': email_user,
        'password': email_password,
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587
    }


# ============================================
# GMAIL APP PASSWORD SETUP INSTRUCTIONS
# ============================================

"""
HOW TO GET GMAIL APP PASSWORD:
==============================

1. Go to your Google Account: https://myaccount.google.com/
2. Click "Security" in the left menu
3. Under "Signing in to Google", click "2-Step Verification"
4. Enable 2-Step Verification if not already enabled
5. Go back to Security page
6. Under "Signing in to Google", click "App passwords"
7. Select app: "Mail"
8. Select device: "Other (Custom name)"
9. Enter name: "Smart Bus System"
10. Click "Generate"
11. Copy the 16-character password (no spaces)
12. Use this as EMAIL_PASSWORD environment variable


HOW TO SET ENVIRONMENT VARIABLES:
=================================

WINDOWS (PowerShell):
--------------------
# Temporary (current session only):
$env:EMAIL_USER = "your_email@gmail.com"
$env:EMAIL_PASSWORD = "your_16_char_app_password"

# Permanent (system-wide):
[System.Environment]::SetEnvironmentVariable('EMAIL_USER', 'your_email@gmail.com', 'User')
[System.Environment]::SetEnvironmentVariable('EMAIL_PASSWORD', 'your_16_char_app_password', 'User')


WINDOWS (CMD):
-------------
# Temporary (current session only):
set EMAIL_USER=your_email@gmail.com
set EMAIL_PASSWORD=your_16_char_app_password

# Permanent (system-wide):
setx EMAIL_USER "your_email@gmail.com"
setx EMAIL_PASSWORD "your_16_char_app_password"


LINUX/MAC:
----------
# Temporary (current session only):
export EMAIL_USER="your_email@gmail.com"
export EMAIL_PASSWORD="your_16_char_app_password"

# Permanent (add to ~/.bashrc or ~/.zshrc):
echo 'export EMAIL_USER="your_email@gmail.com"' >> ~/.bashrc
echo 'export EMAIL_PASSWORD="your_16_char_app_password"' >> ~/.bashrc
source ~/.bashrc


USING .env FILE (Recommended for Development):
==============================================

1. Create a file named .env in your project root
2. Add these lines:
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASSWORD=your_16_char_app_password

3. Install python-dotenv:
   pip install python-dotenv

4. Load in your app (add to top of app_fast.py):
   from dotenv import load_dotenv
   load_dotenv()


SECURITY NOTES:
==============

✅ DO:
- Use environment variables for credentials
- Use Gmail App Passwords (not your actual Gmail password)
- Add .env to .gitignore (never commit credentials)
- Use different credentials for development and production

❌ DON'T:
- Hardcode credentials in source code
- Commit .env file to Git
- Share credentials in documentation
- Use your actual Gmail password (use App Password)


EXAMPLE USAGE IN CODE:
=====================

from config_email import get_email_config

# Get email configuration
email_config = get_email_config()

# Use in your email sending code
smtp_server = email_config['smtp_server']
smtp_port = email_config['smtp_port']
sender_email = email_config['user']
sender_password = email_config['password']
"""

# ============================================
# EXPORT CONFIGURATION
# ============================================

# Get configuration when module is imported
EMAIL_CONFIG = get_email_config()

# Print configuration status (without showing password)
print("=" * 60)
print("📧 EMAIL CONFIGURATION")
print("=" * 60)
print(f"Email User: {EMAIL_CONFIG['user']}")
print(f"SMTP Server: {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")
print(f"Password Set: {'Yes' if EMAIL_CONFIG['password'] != 'your_app_password' else 'No (using default)'}")
print("=" * 60)

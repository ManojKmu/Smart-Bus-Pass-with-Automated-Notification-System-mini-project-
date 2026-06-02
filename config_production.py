"""
Production Configuration for www.buspassrenewalnotification.com
"""

# Flask Configuration
SECRET_KEY = 'CHANGE_THIS_TO_RANDOM_STRING_IN_PRODUCTION'  # Generate with: import secrets; secrets.token_hex(32)
DEBUG = False
TESTING = False

# Server Configuration
HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 5000

# Session Configuration
SESSION_TYPE = 'filesystem'
PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
SESSION_COOKIE_SECURE = True  # Only send cookie over HTTPS
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection

# Database Configuration (MySQL)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'smartbus',
    'password': 'YOUR_SECURE_PASSWORD_HERE',  # Change this!
    'database': 'smartbus_db',
    'port': 3306
}

# Email Configuration (Gmail)
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'mk4829779@gmail.com',
    'sender_password': 'cbfiekxqfivdwcjs',  # App password
    'sender_name': 'Smart Bus Pass System'
}

# Google OAuth Configuration
GOOGLE_OAUTH = {
    'client_id': '860458258411-922v35iverv84dui6bg3f9tk7gcu9hqg.apps.googleusercontent.com',
    'authorized_origins': [
        'https://buspassrenewalnotification.com',
        'https://www.buspassrenewalnotification.com'
    ],
    'redirect_uris': [
        'https://buspassrenewalnotification.com/google-callback',
        'https://www.buspassrenewalnotification.com/google-callback'
    ]
}

# Domain Configuration
DOMAIN = 'www.buspassrenewalnotification.com'
BASE_URL = f'https://{DOMAIN}'

# UPI Payment Configuration
UPI_ID = 'mk4829779@paytm'
UPI_NAME = 'Smart Bus Pass'

# Security Headers
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'SAMEORIGIN',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
}

# Logging Configuration
LOG_LEVEL = 'INFO'
LOG_FILE = '/var/log/smartbus/app.log'

# Performance Configuration
SEND_FILE_MAX_AGE_DEFAULT = 31536000  # Cache static files for 1 year
JSON_SORT_KEYS = False  # Don't sort JSON keys for speed
TEMPLATES_AUTO_RELOAD = False  # Disable in production for performance

# Rate Limiting (optional - requires flask-limiter)
RATELIMIT_ENABLED = True
RATELIMIT_DEFAULT = "100 per hour"
RATELIMIT_STORAGE_URL = "memory://"

print("=" * 60)
print("🌐 PRODUCTION CONFIGURATION LOADED")
print("=" * 60)
print(f"Domain: {DOMAIN}")
print(f"Base URL: {BASE_URL}")
print(f"Debug Mode: {DEBUG}")
print(f"Database: {DB_CONFIG['database']}")
print("=" * 60)

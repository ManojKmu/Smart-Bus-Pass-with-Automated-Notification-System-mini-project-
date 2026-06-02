"""
Razorpay Configuration for Smart Bus System
Automatically detects environment and uses appropriate keys
"""

import os

# ============================================
# ENVIRONMENT DETECTION
# ============================================

def get_base_url():
    """
    Auto-detect if running on localhost or production
    Returns the appropriate base URL
    """
    # Check environment variable first
    if os.environ.get('PRODUCTION_URL'):
        return os.environ.get('PRODUCTION_URL')
    
    # Check Flask environment
    if os.environ.get('FLASK_ENV') == 'production':
        return 'http://www.buspassrenewal.com'
    
    # Default to localhost for development
    return 'http://127.0.0.1:5000'


def is_production():
    """Check if running in production environment"""
    base_url = get_base_url()
    return 'buspassrenewal.com' in base_url or os.environ.get('FLASK_ENV') == 'production'


# ============================================
# RAZORPAY API KEYS
# ============================================

# LIVE MODE KEYS (for production - REAL PAYMENTS)
# Get these from: https://dashboard.razorpay.com/app/keys (Live Mode)
# Payments will come directly to YOUR bank account linked with Razorpay
RAZORPAY_LIVE_CONFIG = {
    'key_id': 'rzp_live_SK0HYomDu1EiA3',      # Your LIVE key ID
    'key_secret': 'gxoGJzFAsKjtXm3b0Dnaj884',  # Your LIVE key secret
    'enabled': True  # Set to True to accept REAL payments
}

# TEST MODE KEYS (for testing only - NO REAL MONEY)
# Get these from: https://dashboard.razorpay.com/app/keys (Test Mode)
# TEST MODE KEYS (for testing only - NO REAL MONEY)
# Get these from: https://dashboard.razorpay.com/app/keys (Test Mode)
# Use this ONLY for testing before going live
RAZORPAY_TEST_CONFIG = {
    'key_id': 'rzp_test_Shvy7LOBlhYP14',      # Your TEST key ID
    'key_secret': 'UB0Yu1lqywVYVala103icyS3',  # Your TEST key secret
    'enabled': True  # Set to True to test payments
}


# ============================================
# AUTO-SELECT CONFIGURATION
# ============================================

def get_razorpay_config():
    """
    Get appropriate Razorpay configuration based on environment
    Returns test config for localhost, live config for production
    """
    if is_production():
        if not RAZORPAY_LIVE_CONFIG['enabled']:
            print("⚠️  WARNING: Production environment but live keys not enabled!")
            print("   Using test keys for now. Enable live keys after KYC completion.")
            return RAZORPAY_TEST_CONFIG
        return RAZORPAY_LIVE_CONFIG
    else:
        return RAZORPAY_TEST_CONFIG


# ============================================
# WEBHOOK CONFIGURATION
# ============================================

# Webhook secret for verifying Razorpay webhooks
# Get this from: https://dashboard.razorpay.com/app/webhooks
# After creating webhook, Razorpay will provide a secret
WEBHOOK_SECRET = 'https://rainbow-dango-b6c6ec.netlify.app/'  # Replace after creating webhook in Razorpay dashboard

# Webhook URL for production
WEBHOOK_URL_PRODUCTION = 'https://rainbow-dango-b6c6ec.netlify.app/ '

# Webhook URL for ngrok (development/testing)
# Update this with your ngrok URL when testing webhooks locally
WEBHOOK_URL_NGROK = 'https://rainbow-dango-b6c6ec.netlify.app/ '


# ============================================
# MERCHANT INFORMATION (YOUR DETAILS)
# ============================================

MERCHANT_INFO = {
    'name': 'Lingam Manoj Kumar',
    'upi_id': '8340927497@ibl',
    'phone': '8340927497',
    'business_name': 'Smart Bus Pass System',
    'email': 'mk4829779@gmail.com'
}


# ============================================
# PAYMENT SETTINGS
# ============================================

PAYMENT_SETTINGS = {
    'currency': 'INR',
    'auto_capture': True,  # Automatically capture payments
    'payment_methods': ['card', 'netbanking', 'wallet', 'upi'],
    'theme_color': '#667eea',
    'retry_enabled': True,
    'timeout': 900  # 15 minutes
}


# ============================================
# EXPORT CURRENT CONFIGURATION
# ============================================

BASE_URL = get_base_url()
RAZORPAY_CONFIG = get_razorpay_config()
IS_PRODUCTION = is_production()

# Print configuration on import (for debugging)
print("=" * 60)
print("🔐 RAZORPAY CONFIGURATION")
print("=" * 60)
print(f"Environment: {'PRODUCTION' if IS_PRODUCTION else 'DEVELOPMENT'}")
print(f"Base URL: {BASE_URL}")
print(f"Using: {'LIVE' if IS_PRODUCTION and RAZORPAY_LIVE_CONFIG['enabled'] else 'TEST'} keys")
print(f"Key ID: {RAZORPAY_CONFIG['key_id'][:15]}...")
print("=" * 60)


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_callback_url(route='/razorpay-callback'):
    """Get full callback URL for Razorpay"""
    return f"{BASE_URL}{route}"


def get_webhook_url():
    """Get webhook URL for Razorpay dashboard configuration"""
    return f"{BASE_URL}/razorpay-webhook"


def validate_config():
    """Validate that Razorpay configuration is properly set up"""
    config = get_razorpay_config()
    
    if 'XXXXXXXXXXXX' in config['key_id'] or 'YYYYYYYYYYYYYYYY' in config['key_secret']:
        return False, "Razorpay keys not configured. Please update config_razorpay.py with your actual keys."
    
    if IS_PRODUCTION and not RAZORPAY_LIVE_CONFIG['enabled']:
        return False, "Production environment detected but live keys not enabled. Complete KYC and enable live keys."
    
    return True, "Configuration valid"


# ============================================
# USAGE INSTRUCTIONS
# ============================================

"""
SETUP INSTRUCTIONS:
==================

1. CREATE RAZORPAY ACCOUNT:
   - Go to https://razorpay.com/
   - Sign up with your email
   - Verify your email

2. GET TEST KEYS (for localhost):
   - Login to Razorpay Dashboard
   - Go to Settings → API Keys
   - Switch to "Test Mode"
   - Generate Test Keys
   - Copy Key ID and Key Secret
   - Update RAZORPAY_TEST_CONFIG above

3. TEST ON LOCALHOST:
   - Run: python app_fast.py
   - Go to: http://127.0.0.1:5000
   - Make a test payment
   - Use test card: 4111 1111 1111 1111
   - Or test UPI: success@razorpay

4. COMPLETE KYC (for production):
   - Go to Razorpay Dashboard → Account & Settings
   - Complete KYC verification
   - Add bank account details
   - Wait for approval (usually 24-48 hours)

5. GET LIVE KEYS (after KYC):
   - Go to Settings → API Keys
   - Switch to "Live Mode"
   - Generate Live Keys
   - Copy Key ID and Key Secret
   - Update RAZORPAY_LIVE_CONFIG above
   - Set 'enabled': True

6. DEPLOY TO PRODUCTION:
   - Set environment variable:
     export PRODUCTION_URL=http://www.buspassrenewal.com
     export FLASK_ENV=production
   - Or update your deployment config
   - Restart server

7. CONFIGURE WEBHOOKS (optional but recommended):
   - Go to Settings → Webhooks
   - Add webhook URL: http://www.buspassrenewal.com/razorpay-webhook
   - Select events: payment.captured, payment.failed
   - Copy webhook secret
   - Update WEBHOOK_SECRET above

TEST CREDENTIALS:
================
Test Card Number: 4111 1111 1111 1111
CVV: Any 3 digits
Expiry: Any future date
Test UPI: success@razorpay

ENVIRONMENT VARIABLES:
=====================
For production deployment, set:
- PRODUCTION_URL=http://www.buspassrenewal.com
- FLASK_ENV=production

The system will automatically:
✅ Detect environment (localhost vs production)
✅ Use appropriate Razorpay keys
✅ Generate correct callback URLs
✅ Handle test vs live payments
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import random
import smtplib
from email.mime.text import MIMEText
import os
import datetime
import json
import threading
from database import db  # Import MySQL database

app = Flask(__name__, template_folder='templates', static_folder='static')

# Secret key for session management
app.secret_key = 'smartbus_secret_key_2026_secure'

# Optimize Flask for better performance
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # Cache static files for 1 year
app.config['JSON_SORT_KEYS'] = False  # Don't sort JSON keys for speed

otp_store = {}   # temporary OTP storage (for mini project)

# ---------- USER PASS STORAGE (DATABASE) ----------
# Store user passes in memory (in production, use a real database)
user_passes_db = {}  # Keep for backward compatibility

@app.route("/save-user-pass", methods=["POST"])
def save_user_pass():
    """Save user pass to backend database"""
    try:
        data = request.get_json()
        email = data.get('email')
        pass_data = data.get('pass')
        
        if not email or not pass_data:
            return {"success": False, "error": "Missing email or pass data"}, 400
        
        email_lower = email.lower().strip()
        
        # Initialize user's passes list if not exists
        if email_lower not in user_passes_db:
            user_passes_db[email_lower] = []
        
        # Add pass to user's passes
        user_passes_db[email_lower].append(pass_data)
        
        print(f"✅ Pass saved to memory for {email_lower}: {pass_data.get('type')}")
        print(f"📊 Total passes for {email_lower}: {len(user_passes_db[email_lower])}")
        
        # Save to MySQL database for persistent storage
        try:
            # Extract clean price (remove ₹ symbol)
            price_str = pass_data.get('price', '0')
            if isinstance(price_str, str):
                price_str = price_str.replace('₹', '').replace(',', '').strip()
            
            # Default payment method and transaction ID
            payment_method = pass_data.get('paymentMethod', 'UPI')
            transaction_id = pass_data.get('transactionId', f"TXN{int(datetime.datetime.now().timestamp())}")
            
            db.create_pass(
                user_email=email_lower,
                pass_type=pass_data.get('type', 'Unknown Pass'),
                price=float(price_str) if price_str else 0.0,
                route=pass_data.get('route', 'City Route'),
                distance=float(pass_data.get('distance', 0)),
                expiry_date=pass_data.get('expiryDate', datetime.datetime.now().isoformat()),
                payment_method=payment_method,
                transaction_id=transaction_id
            )
            print(f"✅ Pass successfully saved to MySQL database for {email_lower}")
        except Exception as db_e:
            print(f"⚠️ Could not save to MySQL (using memory fallback): {db_e}")
        
        return {"success": True, "message": "Pass saved successfully"}
        
    except Exception as e:
        print(f"❌ Failed to save pass: {e}")
        return {"success": False, "error": str(e)}, 500

@app.route("/get-user-passes/<email>", methods=["GET"])
def get_user_passes(email):
    """Get all passes for a user from MySQL database"""
    try:
        email_lower = email.lower().strip()
        
        # Get passes from MySQL database
        passes_from_db = db.get_user_passes(email_lower)
        
        # Convert database records to frontend format
        passes = []
        for pass_record in passes_from_db:
            # Calculate days until expiry
            expiry_date = pass_record['expiry_date']
            if isinstance(expiry_date, str):
                expiry_date = datetime.datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
            
            now = datetime.datetime.now()
            days_remaining = (expiry_date - now).days
            
            pass_obj = {
                'id': pass_record['id'],
                'type': pass_record['pass_type'],
                'price': f"₹{pass_record['price']}",
                'route': pass_record['route'] or 'All City Routes',
                'distance': pass_record['distance'] or '0',
                'purchaseDate': pass_record['purchase_date'].isoformat() if pass_record['purchase_date'] else '',
                'expiryDate': expiry_date.isoformat(),
                'paymentMethod': pass_record['payment_method'] or 'UPI',
                'merchantName': 'Lingam Manoj Kumar',
                'status': pass_record['status'],
                'daysRemaining': days_remaining
            }
            
            # Add expiry warning flag
            pass_obj['is_expiring_soon'] = 0 <= days_remaining <= 7
            
            passes.append(pass_obj)
        
        print(f"[DATA] Retrieved {len(passes)} passes from MySQL for {email_lower}")
        
        return {
            "success": True,
            "passes": passes,
            "count": len(passes)
        }
        
    except Exception as e:
        print(f"❌ Failed to get passes from MySQL: {e}")
        # Fallback to in-memory storage
        email_lower = email.lower().strip()
        passes = user_passes_db.get(email_lower, [])
        return {
            "success": True,
            "passes": passes,
            "count": len(passes)
        }

# ---------- ANALYTICS FUNCTIONS (DISABLED FOR SPEED) ----------
def track_user_visit(email=None, action="visit"):
    """Lightweight user tracking - disabled for performance"""
    pass

def get_analytics_summary():
    """Minimal analytics for speed"""
    return {
        'total_visits': 0,
        'total_unique_users': 0,
        'active_users_24h': 0,
        'today_stats': {'visits': 0, 'unique_users': 0, 'logins': 0, 'signups': 0},
        'daily_stats': {},
        'recent_logins': [],
        'active_users': []
    }

# ---------- ANALYTICS ROUTES ----------
@app.route("/analytics", methods=["GET"])
def analytics_dashboard():
    """Admin analytics dashboard"""
    return render_template('analytics.html')

@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    """API endpoint to get analytics data"""
    try:
        summary = get_analytics_summary()
        return jsonify({"success": True, "data": summary})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/track", methods=["POST"])
def track_action():
    """API endpoint to track user actions"""
    try:
        data = request.get_json()
        email = data.get('email')
        action = data.get('action', 'visit')
        
        track_user_visit(email, action)
        return jsonify({"success": True, "message": "Action tracked"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    
    if not email or not password:
        return render_template("index.html", error="Please enter both email and password")
    
    email_lower = email.lower().strip()
    password_clean = password.strip()
    
    # Get user accounts (default + new signups)
    user_accounts = getattr(app, 'user_accounts', {
        "mk4829779@gmail.com": "Manoj123",
        "lingammanojkumar178@gmail.com": "Kumar123",
    })
    
    # Check if account exists
    if email_lower in user_accounts:
        if user_accounts[email_lower] == password_clean:
            # Store email in session for frontend access
            session['user_email'] = email_lower
            session['user_name'] = user_accounts.get(email_lower, email_lower.split('@')[0])
            return redirect(url_for('passes'))
        else:
            return render_template("index.html", 
                                 error="Incorrect password. Please try again or use 'Forgot password?' to reset your password.")
    
    # Account doesn't exist - check if it's a Gmail account for auto-creation
    email_domain = email_lower.split('@')[1] if '@' in email_lower else ''
    gmail_domains = ['gmail.com', 'googlemail.com']
    
    if email_domain in gmail_domains:
        # Auto-create Gmail account
        user_accounts[email_lower] = password_clean
        app.user_accounts = user_accounts
        
        # Extract name from email
        username = email_lower.split('@')[0]
        display_name = username.replace('.', ' ').replace('_', ' ').title()
        
        # Create user profile
        user_profiles = getattr(app, 'user_profiles', {})
        user_profiles[email_lower] = {
            'name': display_name,
            'email': email_lower,
            'phone': '',
            'city': '',
            'address': '',
            'updated_at': datetime.datetime.now().isoformat(),
            'account_type': 'gmail_auto'
        }
        app.user_profiles = user_profiles
        
        # Store email in session for frontend access
        session['user_email'] = email_lower
        session['user_name'] = display_name
        
        # Login the user immediately (skip email sending for speed)
        return redirect(url_for('passes'))
    
    else:
        # Not a Gmail account and doesn't exist
        return render_template("index.html", 
                             error=f"No account found with {email}. Please sign up first.")

def verify_google_account(email, password):
    """
    Verify if the email belongs to a valid Google account
    This is a simplified implementation - in production, you'd use Google API
    """
    try:
        # Check if email is a Gmail account or Google Workspace account
        google_domains = ['gmail.com', 'googlemail.com']
        email_domain = email.split('@')[1].lower()
        
        # For Gmail accounts, we'll assume they're valid Google accounts
        if email_domain in google_domains:
            # In a real implementation, you'd verify with Google API
            # For now, we'll create a basic verification
            
            # Extract name from email (simple approach)
            username = email.split('@')[0]
            name_parts = username.replace('.', ' ').replace('_', ' ').split()
            display_name = ' '.join(word.capitalize() for word in name_parts)
            
            return {
                'success': True,
                'name': display_name,
                'email': email,
                'verified': True
            }
        else:
            # For non-Gmail accounts, check if it could be a Google Workspace account
            # This is a simplified check - in production, use Google API
            return {
                'success': False,
                'error': 'Not a recognized Google account domain'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Verification failed: {str(e)}'
        }

def send_google_welcome_email(email, name):
    """Send welcome email to newly verified Google account"""
    try:
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfi ekxq fivd wcjs"
        
        msg = MIMEText(f"""
Hello {name},

Welcome to Smart Bus! Your Google account has been successfully verified and linked.

Your account details:
- Email: {email}
- Account Type: Google Account (Verified)

You can now access all Smart Bus features including:
- Bus pass management
- Pass renewal with OTP verification
- Dashboard and notifications

Thank you for joining Smart Bus!

Best regards,
Smart Bus Team
        """)
        
        msg["Subject"] = "Smart Bus - Google Account Verified & Linked"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Welcome email sent to verified Google account: {email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send welcome email: {e}")
        return False

# ---------- GOOGLE LOGIN VERIFICATION ----------
@app.route("/google-login", methods=["POST"])
def google_login():
    email = request.form.get("email")
    name = request.form.get("name")
    google_id = request.form.get("google_id", "")
    
    print(f"=== GOOGLE LOGIN ATTEMPT ===")
    print(f"Email: {email}")
    print(f"Name: {name}")
    print(f"Google ID: {google_id}")
    print(f"============================")
    
    if email and name:
        email_lower = email.lower().strip()
        
        # Get user accounts (including new signups)
        user_accounts = getattr(app, 'user_accounts', {
            "mk4829779@gmail.com": "Manoj123",
            "lingammanojkumar178@gmail.com": "Kumar123",
        })
        
        # For Google OAuth, we'll create account if it doesn't exist
        # This allows any verified Google user to access the system
        google_password = None  # Initialize password variable
        
        if email_lower not in user_accounts:
            # Create new account with Google details
            # Generate a secure password based on Google ID
            import hashlib
            google_password = f"Google_{hashlib.md5(google_id.encode()).hexdigest()[:8]}"
            user_accounts[email_lower] = google_password
            app.user_accounts = user_accounts
            
            # Also create/update user profile with Google name
            user_profiles = getattr(app, 'user_profiles', {})
            user_profiles[email_lower] = {
                'name': name,  # Use the actual Google name
                'email': email_lower,
                'phone': '',
                'city': '',
                'address': '',
                'updated_at': datetime.datetime.now().isoformat(),
                'account_type': 'google'
            }
            app.user_profiles = user_profiles
            
            print(f"✅ New Google account created for {email}")
            print(f"👤 Profile created with name: {name}")
            print(f"🔑 Generated password: {google_password}")
        else:
            # Update existing profile with Google name if it exists
            user_profiles = getattr(app, 'user_profiles', {})
            if email_lower in user_profiles:
                user_profiles[email_lower]['name'] = name  # Update with Google name
                user_profiles[email_lower]['account_type'] = 'google'
                user_profiles[email_lower]['updated_at'] = datetime.datetime.now().isoformat()
                app.user_profiles = user_profiles
                print(f"✅ Existing Google account login for {email}")
                print(f"👤 Profile updated with name: {name}")
            else:
                # Create profile for existing account
                user_profiles[email_lower] = {
                    'name': name,
                    'email': email_lower,
                    'phone': '',
                    'city': '',
                    'address': '',
                    'updated_at': datetime.datetime.now().isoformat(),
                    'account_type': 'google'
                }
                app.user_profiles = user_profiles
                print(f"✅ Profile created for existing Google account: {email}")
                print(f"👤 Profile created with name: {name}")
            
            # Get existing password for existing accounts
            google_password = user_accounts[email_lower]
        
        # Send welcome email with account details (for both new and existing accounts)
        try:
            SENDER_EMAIL = "mk4829779@gmail.com"
            SENDER_PASSWORD = "cbfi ekxq fivd wcjs"
            
            msg = MIMEText(f"""
Hello {name},

Welcome to Smart Bus! Your Google account has been successfully linked.

Your account details:
- Email: {email}
- Account Type: Google Account (OAuth Verified)
- Alternative Login Password: {google_password}

You can access Smart Bus using either:
1. Google Sign-In (recommended) - Just click "Sign in with Google"
2. Email/Password Login - Use your email and the password above

Features available to you:
- Bus pass management and renewal
- OTP verification for secure transactions
- Dashboard with notifications
- Profile management

To change your alternative password, use the "Forgot Password" option on the login page.

Thank you for joining Smart Bus!

Best regards,
Smart Bus Team
            """)
            
            msg["Subject"] = "Smart Bus - Google Account Successfully Linked"
            msg["From"] = SENDER_EMAIL
            msg["To"] = email_lower
            
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Welcome email sent to {email}")
            
        except Exception as e:
            print(f"❌ Failed to send welcome email: {e}")
        
        # Store email in session for frontend access
        session['user_email'] = email_lower
        session['user_name'] = name
        
        print(f"✅ Google login successful for {email}")
        return redirect(url_for('passes'))
        
    else:
        return render_template("index.html", error="Google login failed. Please try again.")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    """Handle logout and redirect to login page"""
    session.clear()  # Clear session data
    print("🚪 User logged out")
    return redirect(url_for('index'))

# ---------- FAST ROUTE HANDLERS ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/passes")
def passes():
    # Get user email from session
    user_email = session.get('user_email', '')
    user_name = session.get('user_name', '')
    return render_template("passes.html", user_email=user_email, user_name=user_name)

@app.route("/route")
def route():
    return render_template("route_embedded_map.html")

@app.route("/payment")
def payment():
    return render_template("payment.html")

@app.route("/renew-pass")
def renew_pass():
    return render_template("renew-pass.html")

# ---------- SEND RENEW OTP ----------
@app.route("/send-renew-otp", methods=["POST"])
def send_renew_otp():
    user_email = request.form["email"]

    # Validate email format more strictly
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, user_email):
        error_msg = "Please enter a valid email address (e.g., user@gmail.com)."
        return render_template("renew-pass.html", error=error_msg)
    
    # Additional validation: Check if email domain exists (basic check)
    if not any(domain in user_email.lower() for domain in ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com']):
        error_msg = "Please use a valid email provider (Gmail, Yahoo, Outlook, etc.)."
        return render_template("renew-pass.html", error=error_msg)

    otp = random.randint(100000, 999999)
    otp_store[user_email] = otp

    print(f"=== SENDING OTP ===")
    print(f"To: {user_email}")
    print(f"OTP: {otp}")
    print(f"==================")

    # Email configuration - Using YOUR Gmail to send to USER's email
    SENDER_EMAIL = "mk4829779@gmail.com"  # Your Gmail (sender)
    SENDER_PASSWORD = "cbfi ekxq fivd wcjs"  # Your Gmail App Password
    RECIPIENT_EMAIL = user_email  # User's email (recipient)
    
    # Create email message
    msg = MIMEText(f"""
Hello,

Your Smart Bus Pass Renewal OTP is: {otp}

This OTP is valid for 10 minutes.
Please do not share this OTP with anyone.

If you did not request this OTP, please ignore this email.

Thank you for using Smart Bus!

Best regards,
Smart Bus Team
    """)
    msg["Subject"] = "Smart Bus Pass Renewal - OTP Verification"
    msg["From"] = SENDER_EMAIL  # From your Gmail
    msg["To"] = RECIPIENT_EMAIL  # To user's email

    try:
        print(f"📧 Sending from: {SENDER_EMAIL}")
        print(f"📧 Sending to: {RECIPIENT_EMAIL}")
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ OTP sent successfully from {SENDER_EMAIL} to {RECIPIENT_EMAIL}")
        return render_template("renew-verify.html", email=user_email)
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Gmail authentication failed - Check App Password")
        error_msg = "Email service authentication failed. Please contact support."
        return render_template("renew-pass.html", error=error_msg)
        
    except smtplib.SMTPRecipientsRefused:
        print(f"❌ Invalid email address: {RECIPIENT_EMAIL}")
        error_msg = "Invalid email address. Please enter a valid email."
        return render_template("renew-pass.html", error=error_msg)
        
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        error_msg = "Failed to send OTP. Please check your email address and try again."
        return render_template("renew-pass.html", error=error_msg)

# ---------- VERIFY RENEW OTP ----------
@app.route("/verify-renew-otp", methods=["POST"])
def verify_renew_otp():
    email = request.form["email"]
    user_otp = request.form["otp"].strip()  # Remove any extra spaces

    print(f"=== VERIFYING OTP ===")
    print(f"Email: {email}")
    print(f"User entered OTP: '{user_otp}'")
    print(f"Stored OTP: '{otp_store.get(email, 'NOT FOUND')}'")
    print(f"OTP Store contents: {otp_store}")
    print(f"====================")

    if email in otp_store:
        stored_otp = str(otp_store[email]).strip()
        if stored_otp == user_otp:
            print(f"✅ OTP verification successful for {email}")
            # Clear the OTP after successful verification
            del otp_store[email]
            
            # Track renewal OTP verification
            track_user_visit(email, 'renewal_otp_verified')
            
            # Redirect to dashboard with buy-pass section active
            return render_template("dashboard.html", 
                                 success_message="OTP verified successfully! Please select a pass to renew.",
                                 show_buy_pass=True)
        else:
            print(f"❌ OTP mismatch: stored='{stored_otp}', entered='{user_otp}'")
            return render_template("renew-verify.html", 
                                 email=email, 
                                 error="Invalid OTP. Please try again.")
    else:
        print(f"❌ No OTP found for email: {email}")
        return render_template("renew-verify.html", 
                             email=email, 
                             error="OTP expired or not found. Please request a new OTP.")

# ---------- RESEND RENEW OTP ----------
@app.route("/resend-renew-otp", methods=["POST"])
def resend_renew_otp():
    email = request.form.get("email") or request.json.get("email")
    
    if not email:
        return {"success": False, "error": "Email not provided"}, 400
    
    print(f"=== RESENDING OTP ===")
    print(f"To: {email}")
    
    # Generate new OTP
    otp = random.randint(100000, 999999)
    otp_store[email] = otp
    
    print(f"New OTP: {otp}")
    print(f"====================")

    # Email configuration
    SENDER_EMAIL = "mk4829779@gmail.com"
    SENDER_PASSWORD = "cbfi ekxq fivd wcjs"
    RECIPIENT_EMAIL = email
    
    # Create email message
    msg = MIMEText(f"""
Hello,

Your Smart Bus Pass Renewal OTP is: {otp}

This OTP is valid for 10 minutes.
Please do not share this OTP with anyone.

If you did not request this OTP, please ignore this email.

Thank you for using Smart Bus!

Best regards,
Smart Bus Team
    """)
    msg["Subject"] = "Smart Bus Pass Renewal - OTP Verification (Resent)"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL

    try:
        print(f"📧 Resending from: {SENDER_EMAIL} to: {RECIPIENT_EMAIL}")
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ OTP resent successfully to {RECIPIENT_EMAIL}")
        return {"success": True, "message": "OTP sent successfully"}
        
    except Exception as e:
        print(f"❌ Failed to resend OTP: {e}")
        return {"success": False, "error": "Failed to send OTP"}, 500

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    # Check if user came from renewal (has referrer) or new pass
    referrer = request.referrer
    if referrer and 'verify-renew-otp' in referrer:
        message = "Your pass has been successfully renewed!"
        action = "Pass Renewal Successful!"
    else:
        message = "Welcome to Smart Bus Dashboard!"
        action = "New Pass Created Successfully!"
    
    return render_template("dashboard.html", message=message, action=action)

# ---------- FORGOT PASSWORD ----------
@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        # If someone posts to /forgot, redirect to /forgot-password
        return forgot_password()
    return render_template("forgot.html")

@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    email = request.form.get("email")
    
    if not email:
        return render_template("forgot.html", error="Please enter your email address")
    
    email_lower = email.lower().strip()
    
    print(f"=== FORGOT PASSWORD REQUEST ===")
    print(f"Email: {email_lower}")
    print(f"===============================")
    
    # Check if email exists in user accounts (including new signups)
    user_accounts = getattr(app, 'user_accounts', {
        "mk4829779@gmail.com": "Manoj123",
        "lingammanojkumar178@gmail.com": "Kumar123",
    })
    
    if email_lower not in user_accounts:
        print(f"❌ Email not found: {email_lower}")
        return render_template("forgot.html", 
                             error=f"No account found with email {email}. Please sign up first.")
    
    # Generate reset token
    import secrets
    reset_token = secrets.token_urlsafe(32)
    
    # Store reset token temporarily
    reset_tokens = getattr(app, 'reset_tokens', {})
    reset_tokens[email_lower] = {
        'token': reset_token,
        'timestamp': __import__('time').time()
    }
    app.reset_tokens = reset_tokens
    
    # Create reset link
    reset_link = f"http://localhost:5000/reset-password?token={reset_token}&email={email_lower}"
    
    print(f"🔑 Generated reset token: {reset_token}")
    print(f"🔗 Reset link: {reset_link}")
    
    # Email configuration
    SENDER_EMAIL = "mk4829779@gmail.com"
    SENDER_PASSWORD = "cbfi ekxq fivd wcjs"
    RECIPIENT_EMAIL = email_lower
    
    # Create email message
    msg = MIMEText(f"""
Hello,

You requested a password reset for your Smart Bus account.

Click the link below to set a new password:
{reset_link}

This link will expire in 1 hour for security reasons.

If you did not request this password reset, please ignore this email.

Best regards,
Smart Bus Team
    """)
    
    msg["Subject"] = "Smart Bus - Password Reset Link"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    
    try:
        print(f"📧 Sending password reset email to: {RECIPIENT_EMAIL}")
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Password reset email sent successfully to {RECIPIENT_EMAIL}")
        return render_template("forgot.html", 
                             success=f"Password reset link sent to {email}. Please check your email.")
        
    except Exception as e:
        print(f"❌ Failed to send password reset email: {e}")
        return render_template("forgot.html", 
                             error="Failed to send reset email. Please try again later.")

@app.route("/reset-password", methods=["GET"])
def reset_password():
    token = request.args.get('token')
    email = request.args.get('email')
    
    print(f"=== RESET PASSWORD PAGE REQUEST ===")
    print(f"Token: {token}")
    print(f"Email: {email}")
    print(f"===================================")
    
    if not token or not email:
        print("❌ Missing token or email")
        return render_template("forgot.html", error="Invalid reset link. Please request a new one.")
    
    email_lower = email.lower().strip()
    
    # Check if token exists and is valid
    reset_tokens = getattr(app, 'reset_tokens', {})
    
    print(f"📋 Stored tokens: {list(reset_tokens.keys())}")
    
    if email_lower not in reset_tokens:
        print(f"❌ No token found for email: {email_lower}")
        return render_template("forgot.html", error="Invalid or expired reset link. Please request a new one.")
    
    if reset_tokens[email_lower]['token'] != token:
        print(f"❌ Token mismatch for email: {email_lower}")
        return render_template("forgot.html", error="Invalid or expired reset link. Please request a new one.")
    
    # Check if token is expired (1 hour)
    import time
    token_age = time.time() - reset_tokens[email_lower]['timestamp']
    print(f"⏱️ Token age: {token_age:.0f} seconds ({token_age/60:.1f} minutes)")
    
    if token_age > 3600:  # 1 hour
        print(f"❌ Token expired for email: {email_lower}")
        del reset_tokens[email_lower]
        return render_template("forgot.html", error="Reset link has expired (valid for 1 hour). Please request a new one.")
    
    print(f"✅ Token valid, showing reset form for: {email_lower}")
    # Show password reset form
    return render_template("reset-password.html", token=token, email=email_lower)

# ---------- ADDITIONAL ROUTES FOR TEMPLATES ----------

@app.route("/sign-in")
def sign_in():
    return render_template("sign-in.html")


@app.route("/quick-fix-test")
def quick_fix_test():
    return render_template("quick_fix_test.html")

@app.route("/test-complete-flow")
def test_complete_flow():
    return render_template("test_complete_flow.html")

@app.route("/test-route")
def test_route():
    return render_template("test-route.html")

@app.route("/route-google")
def route_google():
    """Route selection page with Google Maps integration"""
    return render_template("route_google_maps.html")

@app.route("/route-leaflet")
def route_leaflet():
    """Route selection page with Leaflet/OpenStreetMap"""
    return render_template("route.html")

# ---------- SEND OTP (Original) ----------
@app.route("/send-otp", methods=["POST"])
def send_otp():
    user_email = request.form["email"]  # User's email address

    otp = random.randint(100000, 999999)
    otp_store[user_email] = otp

    print(f"=== SENDING OTP ===")
    print(f"To: {user_email}")
    print(f"OTP: {otp}")
    print(f"==================")

    # Email configuration - Using YOUR Gmail to send to USER's email
    SENDER_EMAIL = "mk4829779@gmail.com"  # Your Gmail (sender)
    SENDER_PASSWORD = "cbfi ekxq fivd wcjs"  # Your Gmail App Password
    RECIPIENT_EMAIL = user_email  # User's email (recipient)

    # Create email message
    msg = MIMEText(f"""
Hello,

Your Smart Bus Pass OTP is: {otp}

This OTP is valid for 10 minutes.
Please do not share this OTP with anyone.

If you did not request this OTP, please ignore this email.

Thank you for using Smart Bus!

Best regards,
Smart Bus Team
    """)
    msg["Subject"] = "Smart Bus Pass - OTP Verification"
    msg["From"] = SENDER_EMAIL  # From your Gmail
    msg["To"] = RECIPIENT_EMAIL  # To user's email

    try:
        print(f"📧 Sending from: {SENDER_EMAIL}")
        print(f"📧 Sending to: {RECIPIENT_EMAIL}")
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ OTP sent successfully from {SENDER_EMAIL} to {RECIPIENT_EMAIL}")
        return render_template("verify.html", email=user_email)
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Gmail authentication failed - Check App Password")
        return f"<h2>❌ Email service authentication failed</h2><p>Please contact support.</p>"
        
    except smtplib.SMTPRecipientsRefused:
        print(f"❌ Invalid email address: {RECIPIENT_EMAIL}")
        return f"<h2>❌ Invalid email address</h2><p>Please enter a valid email address.</p>"
        
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return f"<h2>❌ Failed to send OTP</h2><p>Please check your email address and try again.</p>"

# ---------- VERIFY OTP (Original) ----------
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    email = request.form["email"]
    user_otp = request.form["otp"]

    if email in otp_store and str(otp_store[email]) == user_otp:
        return f"<h2>OTP Verified ✅<br>Access Granted for Pass</h2>"
    else:
        return "<h2>Invalid OTP ❌</h2>"

# ---------- TEST EMAIL ROUTE ----------
@app.route("/test-email")
def test_email():
    """Test route to check email configuration"""
    try:
        import smtplib
        print("🧪 Testing Gmail SMTP connection...")
        print(f"📧 Email: mk4829779@gmail.com")
        print(f"🔑 Password: cbfi ekxq fivd wcjs")
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("mk4829779@gmail.com", "cbfi ekxq fivd wcjs")
        server.quit()
        
        print("✅ Gmail SMTP connection successful!")
        return "<h2>✅ Email configuration is working!</h2><p>Gmail SMTP connection successful.</p>"
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Gmail Authentication Error: {e}")
        return f"<h2>❌ Gmail Authentication Failed</h2><p>Error: {str(e)}</p><p><strong>Solution:</strong> Check your Gmail App Password</p>"
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return f"<h2>❌ Email configuration failed</h2><p>Error: {str(e)}</p><p>Error type: {type(e).__name__}</p>"

# ---------- EXPIRY NOTIFICATION EMAIL ----------
@app.route("/send-expiry-notification", methods=["POST"])
def send_expiry_notification():
    """Send email notification for pass expiry"""
    try:
        data = request.get_json()
        email = data.get('email')
        pass_type = data.get('passType')
        days_until_expiry = data.get('daysUntilExpiry')
        expiry_date = data.get('expiryDate')
        pass_id = data.get('passId', 'N/A')
        
        if not all([email, pass_type, days_until_expiry, expiry_date]):
            return {"success": False, "error": "Missing required data"}, 400
        
        # Format expiry date
        expiry_date_formatted = expiry_date.split('T')[0]  # Remove time part
        
        # Email configuration
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfi ekxq fivd wcjs"
        
        # Determine urgency level and message
        if days_until_expiry <= 0:
            urgency = "EXPIRED"
            subject_prefix = "🚨 URGENT"
            message_header = "Your Smart Bus Pass has EXPIRED!"
            action_text = "Your pass is no longer valid. Renew immediately to continue using Smart Bus services."
        elif days_until_expiry == 1:
            urgency = "CRITICAL"
            subject_prefix = "🚨 URGENT"
            message_header = "Your Smart Bus Pass expires TOMORROW!"
            action_text = "Your pass will expire in 24 hours. Renew now to avoid service interruption."
        elif days_until_expiry <= 3:
            urgency = "HIGH"
            subject_prefix = "⚠️ IMPORTANT"
            message_header = "Your Smart Bus Pass is expiring soon!"
            action_text = f"Your pass will expire in {days_until_expiry} days. Renew now to ensure uninterrupted service."
        else:
            urgency = "MEDIUM"
            subject_prefix = "📢 REMINDER"
            message_header = "Your Smart Bus Pass renewal reminder"
            action_text = f"Your pass will expire in {days_until_expiry} days. Consider renewing soon."
        
        # Create email message
        msg = MIMEText(f"""
Hello,

{message_header}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PASS DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pass Type: {pass_type}
Pass ID: #{pass_id}
Expiry Date: {expiry_date_formatted}
Days Remaining: {days_until_expiry} day(s)
Status: {urgency}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACTION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{action_text}

HOW TO RENEW YOUR PASS:

1. Visit Smart Bus Dashboard
   → http://localhost:5000/dashboard

2. Navigate to "My Passes" section
   → Click on the pass you want to renew

3. Click the "Renew" button
   → Complete the payment process

4. Your pass will be extended immediately!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RENEWAL BENEFITS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Instant activation - No waiting period
✅ Same great rates - No price increase
✅ Seamless service - No interruption
✅ Email confirmation - Instant receipt

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEED HELP?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 Email: support@smartbus.com
📞 Phone: 1-800-SMARTBUS (24/7)
🌐 Website: http://localhost:5000/
💬 Live Chat: Available on website

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Thank you for choosing Smart Bus!
We appreciate your continued trust in our services.

Best regards,
Smart Bus Team

---
This is an automated notification sent to: {email}
To manage your notification preferences, visit your dashboard.
        """)
        
        msg["Subject"] = f"{subject_prefix}: Smart Bus Pass - {days_until_expiry} Day(s) Remaining"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email
        
        # Send email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ {urgency} expiry notification sent to {email} for {pass_type} ({days_until_expiry} days)")
        return {"success": True, "message": "Notification sent successfully", "urgency": urgency}
        
    except Exception as e:
        print(f"❌ Failed to send expiry notification: {e}")
        return {"success": False, "error": str(e)}, 500

# ---------- CHECK AND SEND EXPIRY NOTIFICATIONS ----------
@app.route("/check-pass-expiry", methods=["POST"])
def check_pass_expiry():
    """Check all user passes and send expiry notifications"""
    try:
        data = request.get_json()
        email = data.get('email')
        passes = data.get('passes', [])
        
        if not email or not passes:
            return {"success": False, "error": "Missing email or passes data"}, 400
        
        notifications_sent = []
        
        for pass_data in passes:
            pass_type = pass_data.get('type')
            expiry_date = pass_data.get('expiryDate')
            pass_id = pass_data.get('id')
            
            if not expiry_date:
                continue
            
            # Calculate days until expiry
            from datetime import datetime
            expiry = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
            now = datetime.now(expiry.tzinfo) if expiry.tzinfo else datetime.now()
            days_until_expiry = (expiry - now).days
            
            # Send notification for passes expiring in 7, 3, 1 days or already expired
            if days_until_expiry in [7, 3, 1] or days_until_expiry <= 0:
                # Send email notification
                notification_result = send_expiry_notification_internal(
                    email, pass_type, days_until_expiry, expiry_date, pass_id
                )
                
                if notification_result['success']:
                    notifications_sent.append({
                        'pass_id': pass_id,
                        'pass_type': pass_type,
                        'days_until_expiry': days_until_expiry,
                        'urgency': notification_result.get('urgency', 'MEDIUM')
                    })
        
        return {
            "success": True, 
            "message": f"Checked {len(passes)} passes, sent {len(notifications_sent)} notifications",
            "notifications": notifications_sent
        }
        
    except Exception as e:
        print(f"❌ Failed to check pass expiry: {e}")
        return {"success": False, "error": str(e)}, 500

def send_expiry_notification_internal(email, pass_type, days_until_expiry, expiry_date, pass_id):
    """Internal function to send expiry notification"""
    try:
        # Format expiry date
        expiry_date_formatted = expiry_date.split('T')[0]
        
        # Email configuration
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfi ekxq fivd wcjs"
        
        # Determine urgency level
        if days_until_expiry <= 0:
            urgency = "EXPIRED"
            subject_prefix = "🚨 URGENT"
            message_header = "Your Smart Bus Pass has EXPIRED!"
        elif days_until_expiry == 1:
            urgency = "CRITICAL"
            subject_prefix = "🚨 URGENT"
            message_header = "Your Smart Bus Pass expires TOMORROW!"
        elif days_until_expiry <= 3:
            urgency = "HIGH"
            subject_prefix = "⚠️ IMPORTANT"
            message_header = "Your Smart Bus Pass is expiring soon!"
        else:
            urgency = "MEDIUM"
            subject_prefix = "📢 REMINDER"
            message_header = "Your Smart Bus Pass renewal reminder"
        
        # Create email message
        msg = MIMEText(f"""
{message_header}

Pass Type: {pass_type}
Pass ID: #{pass_id}
Expiry Date: {expiry_date_formatted}
Days Remaining: {days_until_expiry} day(s)

Renew now at: http://localhost:5000/dashboard

Thank you,
Smart Bus Team
        """)
        
        msg["Subject"] = f"{subject_prefix}: Smart Bus Pass - {days_until_expiry} Day(s) Remaining"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email
        
        # Send email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return {"success": True, "urgency": urgency}
        
    except Exception as e:
        print(f"❌ Failed to send notification: {e}")
        return {"success": False, "error": str(e)}

# ---------- NEW PASSWORD RESET FUNCTIONALITY ----------
@app.route("/set-new-password", methods=["POST"])
def set_new_password():
    token = request.form.get('token')
    email = request.form.get('email')
    new_password = request.form.get('new_password')  # Fixed: was 'password'
    confirm_password = request.form.get('confirm_password')
    
    if not all([token, email, new_password, confirm_password]):
        return render_template("reset-password.html", token=token, email=email,
                             error="Please fill in all fields")
    
    if new_password != confirm_password:
        return render_template("reset-password.html", token=token, email=email,
                             error="Passwords do not match")
    
    if len(new_password) < 6:
        return render_template("reset-password.html", token=token, email=email,
                             error="Password must be at least 6 characters long")
    
    email_lower = email.lower().strip()
    
    # Validate token
    reset_tokens = getattr(app, 'reset_tokens', {})
    if email_lower not in reset_tokens or reset_tokens[email_lower]['token'] != token:
        return render_template("forgot.html", error="Invalid or expired reset link. Please request a new one.")
    
    # Check if token is expired (1 hour)
    import time
    if time.time() - reset_tokens[email_lower]['timestamp'] > 3600:
        del reset_tokens[email_lower]
        return render_template("forgot.html", error="Reset link has expired. Please request a new one.")
    
    # Update password
    user_accounts = getattr(app, 'user_accounts', {
        "mk4829779@gmail.com": "Manoj123",
        "lingammanojkumar178@gmail.com": "Kumar123",
    })
    
    if email_lower not in user_accounts:
        return render_template("forgot.html", error="Account not found. Please sign up first.")
    
    user_accounts[email_lower] = new_password
    app.user_accounts = user_accounts
    
    # Clean up token
    del reset_tokens[email_lower]
    
    print(f"✅ Password updated successfully for {email_lower}")
    print(f"🔑 New password: {new_password}")
    
    # Send confirmation email
    try:
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfi ekxq fivd wcjs"
        
        msg = MIMEText(f"""
Hello,

Your Smart Bus password has been successfully updated!

You can now login with:
- Email: {email_lower}
- New Password: {new_password}

If you did not make this change, please contact support immediately.

Best regards,
Smart Bus Team
        """)
        
        msg["Subject"] = "Smart Bus - Password Successfully Updated"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email_lower
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Password confirmation email sent to {email_lower}")
        
    except Exception as e:
        print(f"❌ Failed to send confirmation email: {e}")
    
    return render_template("index.html", 
                         success=f"Password updated successfully! You can now login with your new password.")

# ---------- TEST ROUTE ----------
@app.route("/test-profile", methods=["GET"])
def test_profile():
    return jsonify({"success": True, "message": "Test route working!"})

# ---------- GET PROFILE INFO ----------
@app.route("/get_profile", methods=["GET"])
def get_profile():
    email = request.args.get('email')
    
    if not email:
        return jsonify({"success": False, "error": "Email not provided"})
    
    email_lower = email.lower().strip()
    
    # Get user profiles
    user_profiles = getattr(app, 'user_profiles', {})
    
    if email_lower in user_profiles:
        profile = user_profiles[email_lower]
        return jsonify({
            "success": True,
            "data": {
                "name": profile['name'],
                "email": profile['email'],
                "phone": profile.get('phone', ''),
                "city": profile.get('city', ''),
                "address": profile.get('address', ''),
                "updated_at": profile.get('updated_at', '')
            }
        })
    else:
        # If no profile exists, create a basic one from email
        username = email_lower.split('@')[0]
        display_name = username.replace('.', ' ').replace('_', ' ').title()
        
        return jsonify({
            "success": True,
            "data": {
                "name": display_name,
                "email": email_lower,
                "phone": "",
                "city": "",
                "address": "",
                "updated_at": ""
            }
        })

# ---------- PROFILE UPDATE ----------
@app.route("/update_profile", methods=["POST"])
def update_profile():
    try:
        print("=== UPDATE PROFILE DEBUG ===")
        print(f"Request method: {request.method}")
        print(f"Content-Type: {request.headers.get('Content-Type')}")
        print(f"Request data: {request.data}")
        
        data = request.get_json()
        print(f"Parsed JSON data: {data}")
        
        if not data:
            print("❌ No data provided")
            return jsonify({"success": False, "error": "No data provided"})
        
        email = data.get("email")
        phone = data.get("phone", "")
        city = data.get("city", "")
        address = data.get("address", "")
        
        print(f"Extracted data - Email: {email}, Phone: {phone}, City: {city}, Address: {address}")
        
        if not email:
            print("❌ Email is required")
            return jsonify({"success": False, "error": "Email is required"})
        
        email_lower = email.lower().strip()
        print(f"Email (normalized): {email_lower}")
        
        # Get user accounts to verify user exists
        user_accounts = getattr(app, 'user_accounts', {
            "mk4829779@gmail.com": "Manoj123",
            "lingammanojkumar178@gmail.com": "Kumar123",
        })
        
        print(f"Available user accounts: {list(user_accounts.keys())}")
        
        # Check if user exists
        if email_lower not in user_accounts:
            print(f"❌ User not found: {email_lower}")
            return jsonify({"success": False, "error": f"User not found: {email_lower}"})
        
        print(f"✅ User found: {email_lower}")
        
        # Get existing profile or create new one
        user_profiles = getattr(app, 'user_profiles', {})
        print(f"Existing profiles: {list(user_profiles.keys())}")
        
        if email_lower in user_profiles:
            # Update existing profile
            print(f"Updating existing profile for: {email_lower}")
            profile = user_profiles[email_lower]
            profile['phone'] = phone
            profile['city'] = city
            profile['address'] = address
            profile['updated_at'] = datetime.datetime.now().isoformat()
        else:
            # Create new profile with basic info
            print(f"Creating new profile for: {email_lower}")
            username = email_lower.split('@')[0]
            display_name = username.replace('.', ' ').replace('_', ' ').title()
            
            user_profiles[email_lower] = {
                'name': display_name,
                'email': email_lower,
                'phone': phone,
                'city': city,
                'address': address,
                'updated_at': datetime.datetime.now().isoformat()
            }
        
        # Update app attributes
        app.user_profiles = user_profiles
        
        print(f"✅ Profile updated successfully for {email_lower}")
        print(f"   Phone: {phone}")
        print(f"   City: {city}")
        print(f"   Address: {address}")
        print("=== END UPDATE PROFILE DEBUG ===")
        
        return jsonify({
            "success": True, 
            "message": "Profile updated successfully",
            "data": {
                "name": user_profiles[email_lower]['name'],
                "email": email_lower,
                "phone": phone,
                "city": city,
                "address": address
            }
        })
        
    except Exception as e:
        print(f"❌ Exception in update_profile: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Server error: {str(e)}"})

# ---------- PROFILE PASSWORD UPDATE ----------
@app.route("/update_password", methods=["POST"])
def update_password():
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "error": "No data provided"})
    
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    user_email = data.get("email")
    
    if not all([current_password, new_password, user_email]):
        return jsonify({"success": False, "error": "All fields are required"})
    
    if len(new_password) < 6:
        return jsonify({"success": False, "error": "New password must be at least 6 characters long"})
    
    # Get user accounts
    user_accounts = getattr(app, 'user_accounts', {
        "mk4829779@gmail.com": "Manoj123",
        "lingammanojkumar178@gmail.com": "Kumar123",
    })
    
    email_lower = user_email.lower().strip()
    
    # Check if user exists
    if email_lower not in user_accounts:
        return jsonify({"success": False, "error": "User not found"})
    
    # Verify current password
    if user_accounts[email_lower] != current_password:
        return jsonify({"success": False, "error": "Current password is incorrect"})
    
    # Update password
    user_accounts[email_lower] = new_password
    app.user_accounts = user_accounts
    
    print(f"✅ Password updated successfully for {email_lower}")
    
    return jsonify({
        "success": True, 
        "message": "Password updated successfully"
    })

if __name__ == "__main__":
    print("🚀 Smart Bus App Starting...")
    print("📧 Email Configuration:")
    print("   - Gmail: mk4829779@gmail.com")
    print("   - App Password: cbfi ekxq fivd wcjs")
    print("🌐 Access your app at: http://localhost:5000/")
    print("🧪 Test email at: http://localhost:5000/test-email")
    print("=" * 50)

# ---------- DEBUG ROUTES ----------
@app.route("/debug-routes")
def debug_routes():
    """Debug route to show all available routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': str(rule)
        })
    
    routes_html = "<h2>Available Routes:</h2><ul>"
    for route in sorted(routes, key=lambda x: x['rule']):
        routes_html += f"<li><strong>{route['rule']}</strong> → {route['endpoint']} ({', '.join(route['methods'])})</li>"
    routes_html += "</ul>"
    
    return f"""
    <html>
    <head><title>Flask Routes Debug</title></head>
    <body>
        <h1>Smart Bus Flask Routes</h1>
        {routes_html}
        <br><br>
        <a href="/">← Back to Home</a>
    </body>
    </html>
    """
# ---------- ADVANCED GOOGLE ACCOUNT VERIFICATION ----------
@app.route("/verify-google-account", methods=["POST"])
def verify_google_account_endpoint():
    """
    Advanced endpoint to verify Google accounts and create them automatically
    This can be called from frontend when user enters email/password
    """
    email = request.form.get("email")
    password = request.form.get("password")
    
    if not email:
        return {"success": False, "error": "Email required"}, 400
    
    email_lower = email.lower().strip()
    
    print(f"=== GOOGLE ACCOUNT VERIFICATION ===")
    print(f"Email: {email_lower}")
    print(f"===================================")
    
    # Check if it's a Google account domain
    google_domains = ['gmail.com', 'googlemail.com']
    email_domain = email_lower.split('@')[1] if '@' in email_lower else ''
    
    if email_domain in google_domains:
        # This is a Gmail account - verify and create
        user_accounts = getattr(app, 'user_accounts', {
            "mk4829779@gmail.com": "Manoj123",
            "lingammanojkumar178@gmail.com": "Kumar123",
        })
        
        if email_lower not in user_accounts:
            # Create account for Gmail user
            if password:
                user_accounts[email_lower] = password
            else:
                # Generate secure password
                import secrets
                user_accounts[email_lower] = f"Gmail{secrets.randbelow(99999):05d}"
            
            app.user_accounts = user_accounts
            
            # Extract name from email
            username = email_lower.split('@')[0]
            display_name = username.replace('.', ' ').replace('_', ' ').title()
            
            # Send verification email
            send_google_verification_email(email_lower, display_name, user_accounts[email_lower])
            
            print(f"✅ Gmail account created and verified: {email_lower}")
            return {
                "success": True, 
                "message": "Google account verified and created",
                "account_type": "gmail",
                "name": display_name
            }
        else:
            print(f"✅ Existing Gmail account found: {email_lower}")
            return {
                "success": True,
                "message": "Existing Google account found",
                "account_type": "existing"
            }
    else:
        # Check if it could be a Google Workspace account
        # In production, you'd use Google API to verify this
        return {
            "success": False,
            "error": "Not a recognized Google account. Please use Gmail or sign up manually."
        }

def send_google_verification_email(email, name, password):
    """Send verification email for automatically created Google accounts"""
    try:
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfi ekxq fivd wcjs"
        
        msg = MIMEText(f"""
Hello {name},

Your Google account has been automatically verified and linked to Smart Bus!

Account Details:
- Email: {email}
- Account Type: Google Account (Auto-Verified)
- Login Password: {password}

How to Access Smart Bus:
1. Google Sign-In: Click "Sign in with Google" (Recommended)
2. Email/Password: Use your email and the password above

Your Smart Bus Features:
✅ Bus pass management and renewal
✅ Secure OTP verification
✅ Personal dashboard and notifications
✅ Profile management
✅ Pass renewal reminders

Security Note: Your account was created because you used a Gmail address. If this wasn't you, please contact our support team.

To change your password, use the "Forgot Password" option on the login page.

Welcome to Smart Bus!

Best regards,
Smart Bus Team
        """)
        
        msg["Subject"] = "Smart Bus - Google Account Auto-Verified & Created"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Google verification email sent to: {email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send Google verification email: {e}")
        return False

# ---------- SMART LOGIN SYSTEM ----------
@app.route("/smart-login", methods=["POST"])
def smart_login():
    """
    Smart login system that automatically handles Google accounts
    """
    email = request.form.get("email")
    password = request.form.get("password")
    
    if not email or not password:
        return render_template("index.html", error="Please enter both email and password")
    
    email_lower = email.lower().strip()
    password_clean = password.strip()
    
    print(f"=== SMART LOGIN ATTEMPT ===")
    print(f"Email: {email_lower}")
    print(f"Password Length: {len(password_clean)}")
    print(f"===========================")
    
    # Get existing accounts
    user_accounts = getattr(app, 'user_accounts', {
        "mk4829779@gmail.com": "Manoj123",
        "lingammanojkumar178@gmail.com": "Kumar123",
    })
    
    # Check if account exists
    if email_lower in user_accounts:
        if user_accounts[email_lower] == password_clean:
            print(f"✅ Existing account login successful: {email_lower}")
            return redirect(url_for('passes'))
        else:
            print(f"❌ Wrong password for existing account: {email_lower}")
            return render_template("index.html", 
                                 error="Incorrect password. Please try again or use 'Forgot password?'")
    
    # Account doesn't exist - check if it's a Google account
    email_domain = email_lower.split('@')[1] if '@' in email_lower else ''
    google_domains = ['gmail.com', 'googlemail.com']
    
    if email_domain in google_domains:
        # Auto-create Google account
        user_accounts[email_lower] = password_clean
        app.user_accounts = user_accounts
        
        # Extract name from email
        username = email_lower.split('@')[0]
        display_name = username.replace('.', ' ').replace('_', ' ').title()
        
        # Send welcome email
        send_google_verification_email(email_lower, display_name, password_clean)
        
        print(f"✅ Google account auto-created and login successful: {email_lower}")
        return redirect(url_for('passes'))
    else:
        # Not a Google account and doesn't exist
        print(f"❌ Account not found and not a Google account: {email_lower}")
        return render_template("index.html", 
                             error=f"No account found with {email}. Please sign up first or use a Gmail address for automatic verification.")
# ---------- DEBUG ACCOUNT INFO ----------
@app.route("/debug-accounts")
def debug_accounts():
    """Debug route to show current user accounts (for development only)"""
    user_accounts = getattr(app, 'user_accounts', {
        "mk4829779@gmail.com": "Manoj123",
        "lingammanojkumar178@gmail.com": "Kumar123",
    })
    
    accounts_html = "<h2>Current User Accounts:</h2><ul>"
    for email, password in user_accounts.items():
        accounts_html += f"<li><strong>{email}</strong> → '{password}' (length: {len(password)})</li>"
    accounts_html += "</ul>"
    
    return f"""
    <html>
    <head><title>Debug Accounts</title></head>
    <body>
        <h1>Smart Bus Account Debug</h1>
        {accounts_html}
        <br><br>
        <p><strong>Instructions:</strong></p>
        <ul>
            <li>Use the exact passwords shown above</li>
            <li>Passwords are case-sensitive</li>
            <li>No extra spaces allowed</li>
        </ul>
        <br>
        <a href="/">← Back to Login</a>
    </body>
    </html>
    """
# ---------- PASSWORD INFO ----------
@app.route("/password-info")
def password_info():
    """Show correct passwords for login"""
    return """
    <html>
    <head><title>Login Information</title></head>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h1>🔐 Correct Login Information</h1>
        
        <h2>Account 1:</h2>
        <p><strong>Email:</strong> mk4829779@gmail.com</p>
        <p><strong>Password:</strong> Manoj123</p>
        
        <h2>Account 2:</h2>
        <p><strong>Email:</strong> lingammanojkumar178@gmail.com</p>
        <p><strong>Password:</strong> Kumar123</p>
        
        <hr>
        <p><strong>Important:</strong></p>
        <ul>
            <li>Passwords are case-sensitive</li>
            <li>Use complete passwords (not partial)</li>
            <li>No extra spaces</li>
        </ul>
        
        <br>
        <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Login</a>
    </body>
    </html>
    """
# ---------- PAYMENT CONFIRMATION EMAIL (OPTIMIZED) ----------
@app.route("/send-payment-confirmation", methods=["POST"])
def send_payment_confirmation():
    """Send email confirmation for successful payment - OPTIMIZED FOR SPEED"""
    try:
        data = request.get_json()
        email = data.get('email')
        pass_data = data.get('pass')
        
        if not email or not pass_data:
            return {"success": False, "error": "Missing required data"}, 400
        
        # INSTANT RESPONSE - Send email in background
        import threading
        
        # Capture data outside of request context
        email_copy = email
        pass_data_copy = pass_data.copy() if pass_data else {}
        
        def send_email_background():
            try:
                # Email configuration
                SENDER_EMAIL = "mk4829779@gmail.com"
                SENDER_PASSWORD = "cbfi ekxq fivd wcjs"
                
                # Format dates
                purchase_date = pass_data_copy.get('purchaseDate', '').split('T')[0]
                expiry_date = pass_data_copy.get('expiryDate', '').split('T')[0]
                
                # Create email message
                msg = MIMEText(f"""
Hello,

🎉 PAYMENT SUCCESSFUL! 🎉

Your Smart Bus Pass has been activated successfully!

📋 Pass Details:
- Receipt No: SB{pass_data_copy.get('id')}
- Pass Type: {pass_data_copy.get('type')}
- Route: {pass_data_copy.get('route', 'All City Routes')}
- Amount Paid: {pass_data_copy.get('price')}
- Payment Method: {pass_data_copy.get('paymentMethod', 'UPI')}
- Merchant: {pass_data_copy.get('merchantName', 'Lingam Manoj Kumar')}

📅 Validity:
- Purchase Date: {purchase_date}
- Valid From: {purchase_date}
- Valid Until: {expiry_date}
- Status: Active

💡 Important Information:
- Your pass is now active and ready to use
- Keep this email as your receipt
- You can download/view your pass anytime from "My Passes"
- Renewal reminders will be sent before expiry

🚌 How to Use:
1. Show this email or your digital pass to the conductor
2. Access your pass anytime at: http://localhost:5000/passes
3. Download the Smart Bus app for easy access

Need Help?
- Customer Support: support@smartbus.com
- Phone: 1-800-SMARTBUS
- Website: http://localhost:5000/

Thank you for choosing Smart Bus!

Best regards,
Smart Bus Team

---
This is an automated confirmation. Please save this email for your records.
                """)
                
                msg["Subject"] = f"✅ Smart Bus Pass Activated - {pass_data_copy.get('type')} (Receipt: SB{pass_data_copy.get('id')})"
                msg["From"] = SENDER_EMAIL
                msg["To"] = email_copy
                
                # Send email with timeout
                server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
                server.quit()
                
                print(f"✅ Payment confirmation sent to {email_copy} for {pass_data_copy.get('type')}")
            except Exception as e:
                print(f"⚠️ Background email failed (non-critical): {e}")
        
        # Start background thread for email
        email_thread = threading.Thread(target=send_email_background)
        email_thread.daemon = True
        email_thread.start()
        
        # INSTANT RESPONSE - Don't wait for email
        print(f"⚡ Payment confirmation queued for {email}")
        return {"success": True, "message": "Confirmation sent successfully"}
        
    except Exception as e:
        print(f"❌ Failed to queue payment confirmation: {e}")
        return {"success": False, "error": str(e)}, 500
# ---------- REAL-TIME DISTANCE CALCULATION ----------
@app.route("/calculate-distance-realtime", methods=["POST"])
def calculate_distance_realtime():
    """Real-time distance calculation with pass-type-based pricing"""
    try:
        print("🔄 Real-time distance calculation route called")
        data = request.get_json()
        print(f"📊 Received data: {data}")
        
        if not data:
            print("❌ No JSON data received")
            return {"success": False, "error": "No data provided"}, 400
        
        origin = data.get('origin')
        destination = data.get('destination')
        pass_type = data.get('pass_type', 'Regular Pass')
        base_price = data.get('base_price', '₹50')
        
        if not origin or not destination:
            print("❌ Missing origin or destination")
            return {"success": False, "error": "Origin and destination required"}, 400
        
        print(f"🗺️ Calculating real-time distance: {origin} → {destination}")
        print(f"🎫 Pass type: {pass_type}, Base price: {base_price}")
        
        # Get real-time distance
        distance_km, travel_time_minutes = get_realtime_distance(origin, destination)
        
        if distance_km is None:
            print("❌ Distance calculation returned None")
            return {"success": False, "error": "Unable to calculate distance for these locations"}, 400
        
        # Calculate fare based on pass type and distance
        fare = calculate_fare_by_pass_type(distance_km, pass_type, base_price)
        
        result = {
            "success": True,
            "distance_km": distance_km,
            "fare": fare,
            "travel_time_minutes": travel_time_minutes,
            "origin": origin,
            "destination": destination,
            "pass_type": pass_type,
            "calculation_method": "Real-time API with Pass-based Pricing"
        }
        
        print(f"✅ Real-time distance calculated successfully:")
        print(f"   Distance: {distance_km} km")
        print(f"   Pass Type: {pass_type}")
        print(f"   Fare: ₹{fare}")
        print(f"   Travel time: {travel_time_minutes} mins")
        
        return result
        
    except Exception as e:
        print(f"❌ Real-time distance calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}, 500

def calculate_fare_by_pass_type(distance, pass_type, base_price):
    """Calculate fare using just the pass amount (not multiplied by distance)"""
    try:
        print(f"💰 Simple fare calculation:")
        print(f"   Distance: {distance} km")
        print(f"   Pass Type: {pass_type}")
        print(f"   Base Price: {base_price}")
        
        # Extract numeric value from base_price (remove ₹ symbol)
        if isinstance(base_price, str):
            pass_amount = float(base_price.replace('₹', '').strip()) if base_price.replace('₹', '').strip() else 50
        else:
            pass_amount = float(base_price) if base_price else 50
        
        print(f"   Pass Amount: ₹{pass_amount}")
        
        # Simple calculation: Just use the pass amount (no distance multiplication)
        final_fare = int(pass_amount)
        
        print(f"   Final Fare: ₹{final_fare} (Pass amount only)")
        
        return final_fare
        
    except Exception as e:
        print(f"❌ Fare calculation error: {e}")
        # Fallback: return 50 as default pass amount
        return 50

def get_realtime_distance(origin, destination):
    """Get real-time distance using Google Maps API or enhanced simulation"""
    try:
        # TODO: Replace with actual Google Maps API call
        # For now, using enhanced coordinate-based calculation
        
        # Coordinate database for accurate calculations
        coordinates = {
            # Telangana locations with precise coordinates
            'warangal': (17.9689, 79.5941),
            'hanumakonda': (17.9784, 79.5941),
            'hyderabad': (17.3850, 78.4867),
            'secunderabad': (17.4399, 78.4983),
            'santosh nagar': (17.3616, 78.4747),
            'santoshnagar': (17.3616, 78.4747),
            'colony kumarwadi': (17.3850, 78.4600),
            'kumarwadi': (17.3850, 78.4600),
            'gachibowli': (17.4399, 78.3482),
            'hitech city': (17.4485, 78.3908),
            'hi-tech city': (17.4485, 78.3908),
            'jubilee hills': (17.4239, 78.4738),
            'banjara hills': (17.4126, 78.4071),
            'ameerpet': (17.4374, 78.4482),
            'kondapur': (17.4616, 78.3436),
            'kukatpally': (17.4850, 78.4138),
            'uppal': (17.4065, 78.5510),
            'dilsukhnagar': (17.3687, 78.5230),
            'dilsukh nagar': (17.3687, 78.5230),
            'airport': (17.2403, 78.4294),
            'rajiv gandhi international airport': (17.2403, 78.4294),
            'shamshabad': (17.2403, 78.4294),
            # Additional common locations
            'madhapur': (17.4483, 78.3915),
            'begumpet': (17.4435, 78.4677),
            'nampally': (17.3753, 78.4744),
            'koti': (17.3753, 78.4744),
            'abids': (17.3753, 78.4744),
            'tank bund': (17.4239, 78.4738),
            'charminar': (17.3616, 78.4747),
            'golconda': (17.3833, 78.4011),
            'mehdipatnam': (17.3969, 78.4386),
            'tolichowki': (17.3969, 78.3886),
            'lb nagar': (17.3297, 78.5518),
            'vanasthalipuram': (17.3297, 78.5718),
            'miyapur': (17.5273, 78.3476),
            'lingampally': (17.4949, 78.2318),
            'panjagutta': (17.4239, 78.4482),
            'somajiguda': (17.4239, 78.4482),
            'sr nagar': (17.4399, 78.4482),
            'erragadda': (17.4500, 78.4300),
            'moosapet': (17.4700, 78.4200),
            'balanagar': (17.4900, 78.4300),
            'jntu': (17.4949, 78.3915),
            'nizampet': (17.5100, 78.3900),
            'bachupally': (17.5400, 78.3700),
            'kompally': (17.5500, 78.4900),
            'alwal': (17.5000, 78.5200),
            'tarnaka': (17.4200, 78.5400),
            'habsiguda': (17.4100, 78.5500),
            'nagole': (17.3700, 78.5700),
            'lbnagar': (17.3297, 78.5518),
            'kothapet': (17.3500, 78.5300),
            'malakpet': (17.3700, 78.4900),
            'chaderghat': (17.3700, 78.4800),
            'osmangunj': (17.3800, 78.4700),
            'afzalgunj': (17.3750, 78.4700),
            'sultan bazaar': (17.3750, 78.4750),
            'paradise': (17.4400, 78.4900),
            'malkajgiri': (17.4500, 78.5300),
            'sanathnagar': (17.4600, 78.4400),
            'moazzam jahi market': (17.3700, 78.4700),
            'lakdi ka pul': (17.3900, 78.4600),
            'masab tank': (17.4000, 78.4500),
            'khairatabad': (17.4100, 78.4600),
            'assembly': (17.4000, 78.4700),
            'necklace road': (17.4200, 78.4700),
            'hussain sagar': (17.4300, 78.4800),
        }
        
        # Normalize location names
        origin_norm = origin.lower().strip()
        dest_norm = destination.lower().strip()
        
        print(f"🔍 Looking up coordinates for: '{origin_norm}' → '{dest_norm}'")
        
        # Find coordinates
        origin_coords = find_coordinates(origin_norm, coordinates)
        dest_coords = find_coordinates(dest_norm, coordinates)
        
        print(f"📍 Origin coords: {origin_coords}")
        print(f"📍 Destination coords: {dest_coords}")
        
        if origin_coords and dest_coords:
            # Calculate distance using Haversine formula
            distance = haversine_distance(
                origin_coords[0], origin_coords[1],
                dest_coords[0], dest_coords[1]
            )
            
            # Estimate travel time based on distance and traffic
            if distance <= 10:
                travel_time = int(distance * 4)  # City traffic: ~15 km/h
            elif distance <= 30:
                travel_time = int(distance * 3)  # Suburban: ~20 km/h
            else:
                travel_time = int(distance * 2)  # Highway: ~30 km/h
            
            print(f"📍 Real-time calculation: {distance:.1f} km, {travel_time} mins")
            return round(distance, 1), travel_time
        
        # Fallback estimation
        print(f"⚠️  No coordinates found, using smart fallback for: {origin} → {destination}")
        distance, time = estimate_distance_fallback(origin_norm, dest_norm)
        print(f"📍 Fallback result: {distance} km, {time} mins")
        return distance, time
        
    except Exception as e:
        print(f"❌ Real-time distance calculation error: {e}")
        return None, None

def find_coordinates(location_name, coordinates_db):
    """Find coordinates for a location with fuzzy matching"""
    # Direct match
    if location_name in coordinates_db:
        return coordinates_db[location_name]
    
    # Partial match
    for key, coords in coordinates_db.items():
        if key in location_name or location_name in key:
            print(f"📍 Partial match: {location_name} → {key}")
            return coords
    
    # Word-based matching
    words = location_name.split()
    for word in words:
        if len(word) > 3:
            for key, coords in coordinates_db.items():
                if word in key or key in word:
                    print(f"📍 Word match: {word} → {key}")
                    return coords
    
    return None

def haversine_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two points using Haversine formula"""
    import math
    
    R = 6371  # Earth's radius in kilometers
    dLat = math.radians(lat2 - lat1)
    dLng = math.radians(lng2 - lng1)
    
    a = (math.sin(dLat/2) * math.sin(dLat/2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLng/2) * math.sin(dLng/2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def estimate_distance_fallback(origin, destination):
    """Fallback distance estimation when coordinates not found"""
    # Known distances for common routes (more accurate)
    known_distances = {
        ('santosh nagar', 'colony kumarwadi'): (5.2, 20),
        ('colony kumarwadi', 'santosh nagar'): (5.2, 20),
        ('santoshnagar', 'kumarwadi'): (5.2, 20),
        ('kumarwadi', 'santoshnagar'): (5.2, 20),
        ('warangal', 'hanumakonda'): (12.5, 35),
        ('hanumakonda', 'warangal'): (12.5, 35),
        ('secunderabad', 'hyderabad'): (15.3, 45),
        ('hyderabad', 'secunderabad'): (15.3, 45),
        ('gachibowli', 'hitech city'): (4.8, 18),
        ('hitech city', 'gachibowli'): (4.8, 18),
        ('gachibowli', 'hi-tech city'): (4.8, 18),
        ('hi-tech city', 'gachibowli'): (4.8, 18),
        ('hyderabad', 'warangal'): (148.0, 180),
        ('warangal', 'hyderabad'): (148.0, 180),
        ('hyderabad', 'airport'): (42.0, 60),
        ('airport', 'hyderabad'): (42.0, 60),
        ('ameerpet', 'secunderabad'): (8.5, 30),
        ('secunderabad', 'ameerpet'): (8.5, 30),
        ('madhapur', 'gachibowli'): (3.5, 15),
        ('gachibowli', 'madhapur'): (3.5, 15),
    }
    
    # Try exact match first
    key = (origin, destination)
    if key in known_distances:
        print(f"✅ Found exact match in known distances: {key}")
        return known_distances[key]
    
    # Try reverse match
    reverse_key = (destination, origin)
    if reverse_key in known_distances:
        print(f"✅ Found reverse match in known distances: {reverse_key}")
        return known_distances[reverse_key]
    
    # Try partial matching
    for (o, d), (dist, time) in known_distances.items():
        if (o in origin or origin in o) and (d in destination or destination in d):
            print(f"✅ Found partial match: {o} ↔ {d}")
            return (dist, time)
    
    # Estimate based on keywords and location types
    long_distance_keywords = ['airport', 'railway', 'station', 'warangal', 'hanumakonda', 'vijayawada', 'tirupati']
    city_keywords = ['hyderabad', 'secunderabad', 'gachibowli', 'hitech', 'hi-tech', 'jubilee', 'banjara', 'ameerpet', 'madhapur', 'kondapur', 'kukatpally']
    
    origin_long = any(keyword in origin for keyword in long_distance_keywords)
    dest_long = any(keyword in destination for keyword in long_distance_keywords)
    origin_city = any(keyword in origin for keyword in city_keywords)
    dest_city = any(keyword in destination for keyword in city_keywords)
    
    if origin_long or dest_long:
        if 'warangal' in origin or 'warangal' in destination:
            print(f"📍 Long distance detected: Warangal route")
            return 148.0, 180  # Hyderabad-Warangal distance
        elif 'airport' in origin or 'airport' in destination:
            print(f"📍 Long distance detected: Airport route")
            return 42.0, 60    # Airport distance
        else:
            print(f"📍 Long distance detected: Other")
            return 65.0, 90    # Other long distance (reduced from 85km)
    elif origin_city and dest_city:
        print(f"📍 City route detected")
        return 12.0, 35        # Within city (reduced from 18km)
    else:
        # Use a more reasonable default for unknown routes
        print(f"📍 Unknown route, using minimal default")
        return 8.0, 25         # Default city distance (reduced from 10km)

def calculate_rtc_fare_backend(distance):
    """Calculate RTC-style fare based on distance"""
    if distance <= 5:
        fare = max(5, round(distance * 2.5))
    elif distance <= 20:
        fare = round(8 + (distance * 1.8))
    elif distance <= 50:
        fare = round(15 + (distance * 1.5))
    else:
        fare = round(25 + (distance * 1.2))
    
    # Apply minimum fare and round to nearest ₹5
    fare = max(fare, 5)
    fare = round(fare / 5) * 5
    
    return fare
    
    return None

def haversine_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two points using Haversine formula"""
    import math
    
    R = 6371  # Earth's radius in kilometers
    dLat = math.radians(lat2 - lat1)
    dLng = math.radians(lng2 - lng1)
    
    a = (math.sin(dLat/2) * math.sin(dLat/2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLng/2) * math.sin(dLng/2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def estimate_distance_fallback(origin, destination):
    """Fallback distance estimation when coordinates not found"""
    # Known distances for common routes
    known_distances = {
        ('santosh nagar', 'colony kumarwadi'): (3.2, 15),
        ('colony kumarwadi', 'santosh nagar'): (3.2, 15),
        ('warangal', 'hanumakonda'): (12.5, 35),
        ('hanumakonda', 'warangal'): (12.5, 35),
        ('secunderabad', 'hyderabad'): (15.3, 45),
        ('hyderabad', 'secunderabad'): (15.3, 45),
    }
    
    key = (origin, destination)
    if key in known_distances:
        return known_distances[key]
    
    # Estimate based on keywords
    long_distance_keywords = ['airport', 'railway', 'station', 'warangal', 'hanumakonda']
    if any(keyword in origin or keyword in destination for keyword in long_distance_keywords):
        return 15.0, 45  # Reduced from 25km for better accuracy
    
    # Default city distance (reduced from 12km for better accuracy)
    return 8.0, 25

# ---------- SIMPLE API TEST ----------
@app.route("/test-api-simple", methods=["GET", "POST"])
def test_api_simple():
    """Simple API test to verify server is working"""
    if request.method == "GET":
        return {"success": True, "message": "API is working", "method": "GET"}, 200
    else:
        data = request.get_json() or {}
        return {
            "success": True, 
            "message": "POST API is working", 
            "received_data": data,
            "method": "POST"
        }, 200

# ---------- PASS SELECTION HANDLER ----------
@app.route("/select-pass", methods=["POST"])
def select_pass():
    """Handle pass selection and store in session"""
    try:
        data = request.get_json()
        pass_type = data.get('pass_type')
        pass_price = data.get('pass_price')
        
        if not pass_type or not pass_price:
            return {"success": False, "error": "Pass type and price required"}, 400
        
        print(f"✅ Pass selected: {pass_type} - {pass_price}")
        
        # In a real application, you'd store this in a session or database
        # For now, we'll just return success and let frontend handle localStorage
        
        return {
            "success": True,
            "message": "Pass selected successfully",
            "pass_type": pass_type,
            "pass_price": pass_price
        }
        
    except Exception as e:
        print(f"❌ Pass selection failed: {e}")
        return {"success": False, "error": str(e)}, 500

@app.route("/simple-distance", methods=["POST", "GET"])
def simple_distance():
    """Simple distance calculation as backup"""
    try:
        if request.method == "GET":
            return {"success": True, "message": "Simple distance API is working"}, 200
            
        data = request.get_json()
        origin = data.get('origin', 'Unknown')
        destination = data.get('destination', 'Unknown')
        
        print(f"🔄 Simple distance calculation: {origin} → {destination}")
        
        # Enhanced distance patterns for realistic simulation
        distances = {
            ('warangal', 'hanumakonda'): 12.5,
            ('hanumakonda', 'warangal'): 12.5,
            ('santosh nagar', 'colony kumarwadi'): 3.2,  # More accurate distance
            ('colony kumarwadi', 'santosh nagar'): 3.2,
            ('santoshnagar', 'kumarwadi'): 3.2,
            ('kumarwadi', 'santoshnagar'): 3.2,
            ('santosh nagar', 'kumarwadi'): 3.2,
            ('kumarwadi', 'santosh nagar'): 3.2,
            ('secunderabad', 'hyderabad'): 15.3,
            ('hyderabad', 'secunderabad'): 15.3,
        }
        
        key = (origin.lower().strip(), destination.lower().strip())
        distance = distances.get(key, 15.0)  # Default 15 km
        
        # RTC-style fare calculation
        if distance <= 5:
            fare = max(5, round(distance * 2.5))
        elif distance <= 20:
            fare = round(8 + (distance * 1.8))
        else:
            fare = round(15 + (distance * 1.5))
        
        # Apply minimum fare and round to nearest ₹5
        fare = max(fare, 5)
        fare = round(fare / 5) * 5
        
        result = {
            "success": True,
            "distance_km": distance,
            "fare": int(fare),
            "travel_time_minutes": int(distance * 2.5),
            "origin": origin,
            "destination": destination
        }
        
        print(f"✅ Simple calculation result: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Simple distance calculation failed: {e}")
        return {"success": False, "error": str(e)}, 500
@app.route("/test-api", methods=["GET"])
def test_api():
    """Simple test API to check if routing is working"""
    return {"success": True, "message": "API is working"}, 200

@app.route("/list-routes", methods=["GET"])
def list_routes():
    """List all registered routes for debugging"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': str(rule)
        })
    return {"routes": routes}, 200

@app.route("/calculate-distance", methods=["POST"])
def calculate_distance():
    """Calculate distance using Google Maps Distance Matrix API"""
    try:
        print("🔄 Distance calculation route called")
        data = request.get_json()
        print(f"📊 Received data: {data}")
        
        origin = data.get('origin')
        destination = data.get('destination')
        
        if not origin or not destination:
            print("❌ Missing origin or destination")
            return {"success": False, "error": "Origin and destination required"}, 400
        
        print(f"🗺️ Calculating distance: {origin} → {destination}")
        
        # Google Maps API Key (you'll need to get this from Google Cloud Console)
        # For demo purposes, we'll simulate the API call
        import random
        import time
        
        # Simulate API delay
        time.sleep(1)
        
        # Simulate distance calculation based on location names
        distance_km = simulate_google_maps_distance(origin, destination)
        
        # Calculate fare using RTC pricing
        base_fare = 10
        per_km_rate = 2
        free_distance = 2
        
        fare = base_fare
        if distance_km > free_distance:
            fare += (distance_km - free_distance) * per_km_rate
        
        # Apply minimum fare
        fare = max(fare, 15)
        fare = round(fare)
        
        # Simulate travel time (rough estimate: 2.5 km per minute in city traffic)
        travel_time_minutes = round(distance_km * 2.5)
        
        print(f"✅ Distance calculated: {origin} → {destination}")
        print(f"   Distance: {distance_km} km")
        print(f"   Fare: ₹{fare}")
        print(f"   Travel time: {travel_time_minutes} mins")
        
        return {
            "success": True,
            "distance_km": distance_km,
            "fare": fare,
            "travel_time_minutes": travel_time_minutes,
            "origin": origin,
            "destination": destination,
            "calculation_method": "Google Maps API Simulation"
        }
        
    except Exception as e:
        print(f"❌ Distance calculation failed: {e}")
        return {"success": False, "error": str(e)}, 500

def simulate_google_maps_distance(origin, destination):
    """Simulate Google Maps distance calculation"""
    print(f"🔍 Simulating distance for: '{origin}' → '{destination}'")
    
    # Common distance patterns for realistic simulation
    distance_patterns = {
        # Existing patterns
        ('city center', 'airport'): 25.2,
        ('railway station', 'tech park'): 15.8,
        ('university', 'shopping mall'): 8.3,
        ('hospital', 'bus terminal'): 12.1,
        ('residential area', 'business district'): 18.5,
        ('airport', 'city center'): 25.2,
        ('tech park', 'railway station'): 15.8,
        ('shopping mall', 'university'): 8.3,
        ('bus terminal', 'hospital'): 12.1,
        ('business district', 'residential area'): 18.5,
        
        # New patterns for your locations - More Accurate
        ('warangal', 'hanumakonda'): 12.5,
        ('hanumakonda', 'warangal'): 12.5,
        ('santosh nagar', 'colony kumarwadi'): 3.2,  # Corrected distance
        ('colony kumarwadi', 'santosh nagar'): 3.2,
        ('santoshnagar', 'kumarwadi'): 3.2,
        ('kumarwadi', 'santoshnagar'): 3.2,
        ('santosh nagar', 'kumarwadi'): 3.2,
        ('kumarwadi', 'santosh nagar'): 3.2,
        
        # More common Indian locations
        ('secunderabad', 'hyderabad'): 15.3,
        ('hyderabad', 'secunderabad'): 15.3,
        ('gachibowli', 'hitech city'): 5.2,
        ('hitech city', 'gachibowli'): 5.2,
        ('jubilee hills', 'banjara hills'): 7.8,
        ('banjara hills', 'jubilee hills'): 7.8,
    }
    
    # Normalize location names for matching
    origin_norm = origin.lower().strip()
    dest_norm = destination.lower().strip()
    
    print(f"🔍 Normalized: '{origin_norm}' → '{dest_norm}'")
    
    # Check for exact matches first
    for (loc1, loc2), distance in distance_patterns.items():
        if (origin_norm == loc1 and dest_norm == loc2) or (origin_norm == loc2 and dest_norm == loc1):
            print(f"✅ Exact match found: {distance} km")
            return distance
    
    # Check for partial matches (contains)
    for (loc1, loc2), distance in distance_patterns.items():
        if ((loc1 in origin_norm or origin_norm in loc1) and 
            (loc2 in dest_norm or dest_norm in loc2)) or \
           ((loc2 in origin_norm or origin_norm in loc2) and 
            (loc1 in dest_norm or dest_norm in loc1)):
            print(f"✅ Partial match found: {distance} km")
            return distance
    
    # Estimate based on location types
    long_distance_keywords = ['airport', 'railway', 'station', 'terminal']
    medium_distance_keywords = ['mall', 'hospital', 'university', 'park', 'tech', 'nagar', 'colony']
    
    origin_has_long = any(keyword in origin_norm for keyword in long_distance_keywords)
    dest_has_long = any(keyword in dest_norm for keyword in long_distance_keywords)
    origin_has_medium = any(keyword in origin_norm for keyword in medium_distance_keywords)
    dest_has_medium = any(keyword in dest_norm for keyword in medium_distance_keywords)
    
    import random
    
    if origin_has_long or dest_has_long:
        distance = round(20 + random.uniform(0, 15), 1)  # 20-35 km
        print(f"✅ Long distance estimate: {distance} km")
        return distance
    elif origin_has_medium or dest_has_medium:
        distance = round(10 + random.uniform(0, 10), 1)  # 10-20 km
        print(f"✅ Medium distance estimate: {distance} km")
        return distance
    else:
        distance = round(5 + random.uniform(0, 10), 1)   # 5-15 km
        print(f"✅ Short distance estimate: {distance} km")
        return distance

# ---------- UPI PAYMENT REDIRECTION ----------
@app.route("/initiate-upi-payment", methods=["POST"])
def initiate_upi_payment():
    """Generate UPI payment link for real payment apps"""
    try:
        data = request.get_json()
        upi_app = data.get('upi_app')  # phonepe, gpay, paytm, etc.
        amount = data.get('amount')
        pass_type = data.get('pass_type', 'Bus Pass')
        route = data.get('route', '')
        distance = data.get('distance', '0')
        
        if not upi_app or not amount:
            return {"success": False, "error": "UPI app and amount required"}, 400
        
        # UPI payment details - Your IBL UPI credentials
        upi_id = "8340927497@ibl"
        merchant_name = "Lingam Manoj Kumar"
        phone = "8340927497"
        
        # Create description with route info
        description = f"Smart Bus {pass_type}"
        if route and distance != '0':
            description += f" - {route} ({distance}km)"
        
        # Generate UPI payment URL
        upi_url = generate_upi_payment_url(upi_app, upi_id, merchant_name, amount, description)
        
        print(f"✅ UPI payment initiated: {upi_app} - ₹{amount}")
        
        return {
            "success": True,
            "upi_url": upi_url,
            "upi_id": upi_id,
            "merchant_name": merchant_name,
            "phone": phone,
            "amount": amount,
            "app": upi_app,
            "description": description,
            "route": route,
            "distance": distance
        }
        
    except Exception as e:
        print(f"❌ UPI payment initiation failed: {e}")
        return {"success": False, "error": str(e)}, 500

def generate_upi_payment_url(upi_app, upi_id, merchant_name, amount, description):
    """Generate UPI payment URL for different apps - OPTIMIZED VERSION"""
    
    # Pre-encode parameters once
    encoded_merchant = merchant_name.replace(" ", "%20")
    encoded_description = description.replace(" ", "%20")
    
    # Base UPI URL format (universal)
    base_upi_url = f"upi://pay?pa={upi_id}&pn={encoded_merchant}&am={amount}&cu=INR&tn={encoded_description}"
    
    # Simplified app-specific URLs for better performance
    app_urls = {
        'phonepe': f"phonepe://pay?pa={upi_id}&pn={encoded_merchant}&am={amount}&cu=INR&tn={encoded_description}",
        'gpay': f"tez://upi/pay?pa={upi_id}&pn={encoded_merchant}&am={amount}&cu=INR&tn={encoded_description}",
        'paytm': f"paytmmp://pay?pa={upi_id}&pn={encoded_merchant}&am={amount}&cu=INR&tn={encoded_description}",
        'bhim': f"bhim://pay?pa={upi_id}&pn={encoded_merchant}&am={amount}&cu=INR&tn={encoded_description}",
        'other': base_upi_url
    }
    
    # Return the appropriate URL or default to base UPI URL
    selected_url = app_urls.get(upi_app.lower(), base_upi_url)
    
    return selected_url

# ---------- PAYMENT COMPLETION ----------
@app.route("/complete-payment", methods=["POST"])
def complete_payment():
    """Complete payment and generate receipt - ULTRA FAST"""
    try:
        data = request.get_json()
        
        # Get payment details
        pass_type = data.get('pass_type', 'Daily Pass')
        amount = data.get('amount', '25')
        route = data.get('route', 'City Route')
        distance = data.get('distance', '0')
        payment_method = data.get('payment_method', 'UPI')
        
        # Get user info from session or request
        user_email = session.get('user_email') or data.get('user_email')
        user_name = session.get('user_name') or data.get('user_name', 'Smart Bus User')
        
        print(f"⚡ Fast payment processing: {pass_type} - ₹{amount} for {user_name}")
        
        # Generate receipt (fast - no I/O)
        receipt = generate_payment_receipt(pass_type, amount, route, distance, payment_method, user_name, user_email)
        
        # INSTANT RESPONSE - Process everything in background
        if user_email:
            import threading
            
            # Capture data outside of request context
            email_copy = user_email
            name_copy = user_name
            receipt_copy = receipt.copy()
            
            def process_payment_background():
                try:
                    # Send email (no request context needed)
                    send_payment_success_email(email_copy, name_copy, receipt_copy)
                    print(f"✅ Background processing complete for {email_copy}")
                except Exception as e:
                    print(f"⚠️ Background processing failed (non-critical): {e}")
            
            # Start background processing
            bg_thread = threading.Thread(target=process_payment_background)
            bg_thread.daemon = True
            bg_thread.start()
            print(f"⚡ Background processing started for {user_email}")
        
        # INSTANT RESPONSE - Don't wait for email/DB
        return {
            "success": True,
            "message": "Payment completed successfully!",
            "receipt": receipt,
            "redirect_url": "/dashboard"
        }
        
    except Exception as e:
        print(f"❌ Payment completion failed: {e}")
        return {"success": False, "error": str(e)}, 500

def generate_payment_receipt(pass_type, amount, route, distance, payment_method, user_name, user_email):
    """Generate a detailed payment receipt"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    
    # Calculate expiry date based on pass type
    if 'Daily' in pass_type:
        expiry_date = now + timedelta(days=1)
    elif 'Weekly' in pass_type:
        expiry_date = now + timedelta(days=7)
    elif 'Monthly' in pass_type:
        expiry_date = now + timedelta(days=30)
    elif 'Quarterly' in pass_type:
        expiry_date = now + timedelta(days=90)
    elif 'Annual' in pass_type:
        expiry_date = now + timedelta(days=365)
    else:
        expiry_date = now + timedelta(days=1)
    
    receipt = {
        "receipt_number": f"SB{int(now.timestamp())}",
        "transaction_id": f"TXN{int(now.timestamp())}",
        "date": now.strftime("%Y-%m-%d %H:%M:%S"),
        "user_name": user_name,
        "user_email": user_email,
        "pass_type": pass_type,
        "amount": amount,
        "route": route,
        "distance": distance,
        "payment_method": payment_method,
        "merchant_name": "Lingam Manoj Kumar",
        "merchant_upi": "8340927497@ibl",
        "merchant_phone": "8340927497",
        "purchase_date": now.strftime("%Y-%m-%d"),
        "expiry_date": expiry_date.strftime("%Y-%m-%d"),
        "status": "COMPLETED",
        "validity_days": (expiry_date - now).days
    }
    
    print(f"📄 Receipt generated: {receipt['receipt_number']}")
    return receipt

def send_email(recipient_email, subject, html_body, attachment_html=None, attachment_name=None):
    """Send HTML email using Gmail SMTP with optional HTML attachment - OPTIMIZED"""
    try:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders
        import smtplib
        
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfi ekxq fivd wcjs"
        
        # Create multipart message
        msg = MIMEMultipart('mixed')
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient_email
        
        # Attach HTML body
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        # Attach HTML file if provided
        if attachment_html and attachment_name:
            attachment = MIMEBase('text', 'html')
            attachment.set_payload(attachment_html.encode('utf-8'))
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', f'attachment; filename="{attachment_name}"')
            msg.attach(attachment)
        
        # Send email with optimized connection settings
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)  # Added timeout
        server.set_debuglevel(0)  # Disable debug output for speed
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email to {recipient_email}: {e}")
        return False

def send_payment_success_email(user_email, user_name, receipt):
    """Send payment success email with TSRTC ticket (Gmail-compatible) + HTML attachment"""
    try:
        subject = f"🎫 Your TSRTC Bus Pass - {receipt['pass_type']}"
        
        # Generate pass ID if not present
        pass_id = receipt.get('pass_id', f"TSRTC{receipt['receipt_number']}")
        
        # Create standalone ticket HTML for attachment
        ticket_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TSRTC Bus Pass - {receipt['pass_type']}</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: #f0f0f0;
            font-family: Arial, sans-serif;
        }}
        .ticket-container {{
            max-width: 800px;
            margin: 0 auto;
            background: linear-gradient(135deg, #ffb6d9 0%, #ffc0e0 25%, #d4f1d4 50%, #b8e6b8 75%, #ffb6d9 100%);
            border-radius: 10px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        .stamp {{
            width: 200px;
            height: 200px;
            border: 8px solid rgba(233, 30, 99, 0.3);
            border-radius: 50%;
            margin: 0 auto 30px auto;
            padding: 30px;
            text-align: center;
            background: rgba(255, 255, 255, 0.5);
        }}
        .stamp-icon {{ font-size: 50px; margin-bottom: 10px; }}
        .stamp-text {{ font-size: 16px; font-weight: bold; color: #e91e63; line-height: 1.4; }}
        .header {{ text-align: right; margin-bottom: 30px; }}
        .pass-id {{ font-size: 24px; font-weight: bold; color: #333; letter-spacing: 2px; }}
        .tsrtc-logo {{ font-size: 40px; font-weight: bold; color: #e91e63; margin: 10px 0; }}
        .subtitle {{ font-size: 14px; color: #666; }}
        .pass-type {{ text-align: center; background: #e91e63; color: white; padding: 20px; border-radius: 10px; font-size: 24px; font-weight: bold; margin-bottom: 30px; }}
        .details {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 30px; }}
        .detail-box {{ background: rgba(255, 255, 255, 0.9); padding: 15px; border-radius: 8px; }}
        .detail-label {{ font-size: 11px; color: #666; text-transform: uppercase; margin-bottom: 5px; }}
        .detail-value {{ font-size: 16px; font-weight: bold; color: #333; }}
        .route-box {{ background: #fff3cd; padding: 20px; border-radius: 10px; border-left: 5px solid #e91e63; margin-bottom: 30px; }}
        .qr-section {{ text-align: center; background: rgba(255, 255, 255, 0.9); padding: 20px; border-radius: 10px; }}
        .qr-code {{ width: 150px; height: 150px; border: 3px solid #e91e63; border-radius: 8px; margin: 10px auto; }}
        .footer {{ text-align: center; font-size: 11px; color: #666; margin-top: 30px; padding-top: 20px; border-top: 2px solid #e1e5e9; }}
    </style>
</head>
<body>
    <div class="ticket-container">
        <div class="stamp">
            <div class="stamp-icon">🏛️</div>
            <div class="stamp-text">GOVERNMENT OF<br>TELANGANA<br>TSRTC<br>AUTHORIZED</div>
        </div>
        
        <div class="header">
            <div class="pass-id">{pass_id}</div>
            <div class="tsrtc-logo">TSRTC</div>
            <div class="subtitle">Telangana State Road Transport Corporation</div>
        </div>
        
        <div class="pass-type">{receipt['pass_type']}</div>
        
        <div class="details">
            <div class="detail-box">
                <div class="detail-label">Passenger Name</div>
                <div class="detail-value">{user_name}</div>
            </div>
            <div class="detail-box">
                <div class="detail-label">Email</div>
                <div class="detail-value">{user_email}</div>
            </div>
            <div class="detail-box">
                <div class="detail-label">Distance</div>
                <div class="detail-value">{receipt['distance']} km</div>
            </div>
            <div class="detail-box">
                <div class="detail-label">Amount Paid</div>
                <div class="detail-value">₹{receipt['amount']}</div>
            </div>
            <div class="detail-box">
                <div class="detail-label">Purchase Date</div>
                <div class="detail-value">{receipt['purchase_date']}</div>
            </div>
            <div class="detail-box">
                <div class="detail-label">Valid Until</div>
                <div class="detail-value">{receipt['expiry_date']}</div>
            </div>
        </div>
        
        <div class="route-box">
            <div class="detail-label">Route</div>
            <div class="detail-value" style="color: #e91e63; font-size: 18px;">{receipt['route']}</div>
        </div>
        
        <div class="qr-section">
            <div class="detail-label">Scan QR Code to Verify</div>
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=TSRTC-Pass-{pass_id}-{user_email}" 
                 alt="QR Code" 
                 class="qr-code">
            <div style="font-size: 10px; color: #999; margin-top: 10px;">Scan to verify pass authenticity</div>
        </div>
        
        <div class="footer">
            This is a computer-generated pass. Valid only with proper identification.<br>
            For queries: support@tsrtc.telangana.gov.in | Helpline: 040-23450033<br><br>
            Receipt No: {receipt['receipt_number']} | Transaction ID: {receipt['transaction_id']}
        </div>
    </div>
</body>
</html>
        """
        
        # Gmail-compatible HTML email body with attachment note
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f0f0f0; font-family: Arial, sans-serif;">
    
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f0f0f0; padding: 20px 0;">
        <tr>
            <td align="center">
                
                <!-- Email Header -->
                <table width="600" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 20px;">
                    <tr>
                        <td align="center">
                            <h1 style="color: #e91e63; margin: 0 0 10px 0; font-size: 28px;">🎉 Payment Successful!</h1>
                            <p style="color: #666; margin: 0; font-size: 14px;">Your TSRTC Bus Pass is now active and ready to use</p>
                        </td>
                    </tr>
                </table>
                
                <!-- Important Note about Attachment -->
                <table width="600" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 20px;">
                    <tr>
                        <td style="background-color: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ff9800;">
                            <p style="margin: 0; font-size: 13px; color: #856404; line-height: 1.6;">
                                <strong>📎 Your Ticket is Attached!</strong><br>
                                • Open the attached HTML file (TSRTC_Pass_{pass_id}.html) to view your full ticket<br>
                                • If images don't load below, click "Display images" in your email client<br>
                                • Save the attachment for offline access
                            </p>
                        </td>
                    </tr>
                </table>
                
                <!-- TSRTC Ticket -->
                <table width="600" cellpadding="0" cellspacing="0" border="0" style="background: linear-gradient(135deg, #ffb6d9 0%, #ffc0e0 25%, #d4f1d4 50%, #b8e6b8 75%, #ffb6d9 100%); border-radius: 10px; overflow: hidden;">
                    <tr>
                        <td style="padding: 40px 30px; background-color: rgba(255, 255, 255, 0.9);">
                            
                            <!-- Government Stamp Watermark (Simplified for Gmail) -->
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 20px;">
                                <tr>
                                    <td align="center">
                                        <div style="width: 200px; height: 200px; border: 8px solid rgba(233, 30, 99, 0.2); border-radius: 50%; margin: 0 auto; padding: 30px; text-align: center;">
                                            <div style="font-size: 40px; margin-bottom: 10px;">🏛️</div>
                                            <div style="font-size: 14px; font-weight: bold; color: rgba(233, 30, 99, 0.6); line-height: 1.4;">
                                                GOVERNMENT OF<br>TELANGANA<br>TSRTC<br>AUTHORIZED
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- TSRTC Header -->
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 20px;">
                                <tr>
                                    <td align="right">
                                        <div style="font-size: 20px; font-weight: bold; color: #333; letter-spacing: 2px; margin-bottom: 5px;">{pass_id}</div>
                                        <div style="font-size: 32px; font-weight: bold; color: #e91e63; margin-bottom: 5px;">TSRTC</div>
                                        <div style="font-size: 12px; color: #666;">Telangana State Road Transport Corporation</div>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Pass Type -->
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 20px;">
                                <tr>
                                    <td align="center" style="background-color: #e91e63; padding: 15px; border-radius: 8px;">
                                        <div style="font-size: 20px; font-weight: bold; color: white;">{receipt['pass_type']}</div>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Pass Details -->
                            <table width="100%" cellpadding="10" cellspacing="0" border="0" style="margin-bottom: 20px;">
                                <tr>
                                    <td width="50%" style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; vertical-align: top;">
                                        <div style="font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 5px;">PASSENGER NAME</div>
                                        <div style="font-size: 14px; font-weight: bold; color: #333;">{user_name}</div>
                                    </td>
                                    <td width="50%" style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; vertical-align: top;">
                                        <div style="font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 5px;">EMAIL</div>
                                        <div style="font-size: 14px; font-weight: bold; color: #333;">{user_email}</div>
                                    </td>
                                </tr>
                                <tr><td colspan="2" height="10"></td></tr>
                                <tr>
                                    <td width="50%" style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; vertical-align: top;">
                                        <div style="font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 5px;">DISTANCE</div>
                                        <div style="font-size: 14px; font-weight: bold; color: #333;">{receipt['distance']} km</div>
                                    </td>
                                    <td width="50%" style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; vertical-align: top;">
                                        <div style="font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 5px;">AMOUNT PAID</div>
                                        <div style="font-size: 14px; font-weight: bold; color: #333;">₹{receipt['amount']}</div>
                                    </td>
                                </tr>
                                <tr><td colspan="2" height="10"></td></tr>
                                <tr>
                                    <td width="50%" style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; vertical-align: top;">
                                        <div style="font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 5px;">PURCHASE DATE</div>
                                        <div style="font-size: 14px; font-weight: bold; color: #333;">{receipt['purchase_date']}</div>
                                    </td>
                                    <td width="50%" style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; vertical-align: top;">
                                        <div style="font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 5px;">VALID UNTIL</div>
                                        <div style="font-size: 14px; font-weight: bold; color: #333;">{receipt['expiry_date']}</div>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Route Section -->
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 20px;">
                                <tr>
                                    <td style="background-color: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #e91e63;">
                                        <div style="font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 5px;">ROUTE</div>
                                        <div style="font-size: 16px; font-weight: bold; color: #e91e63;">{receipt['route']}</div>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- QR Code Section -->
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 20px;">
                                <tr>
                                    <td align="center" style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                                        <div style="font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 10px;">SCAN QR CODE TO VERIFY</div>
                                        <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=TSRTC-Pass-{pass_id}-{user_email}" 
                                             alt="QR Code" 
                                             width="150" 
                                             height="150"
                                             style="border: 3px solid #e91e63; border-radius: 8px; display: block; margin: 0 auto;">
                                        <div style="font-size: 10px; color: #999; margin-top: 10px;">Scan to verify pass authenticity</div>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Footer Text -->
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td align="center" style="padding-top: 20px; border-top: 2px solid #e1e5e9;">
                                        <p style="font-size: 10px; color: #999; margin: 0; line-height: 1.6;">
                                            This is a computer-generated pass. Valid only with proper identification.<br>
                                            For queries: support@tsrtc.telangana.gov.in | Helpline: 040-23450033
                                        </p>
                                    </td>
                                </tr>
                            </table>
                            
                        </td>
                    </tr>
                </table>
                
                <!-- Email Footer -->
                <table width="600" cellpadding="0" cellspacing="0" border="0" style="margin-top: 20px;">
                    <tr>
                        <td align="center">
                            <p style="color: #666; font-size: 14px; margin: 0 0 15px 0; line-height: 1.6;">
                                Thank you for choosing TSRTC Smart Bus! 🚌<br>
                                Your pass is now active and ready to use.
                            </p>
                            <table cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td align="center" style="background-color: #4CAF50; border-radius: 25px;">
                                        <a href="http://localhost:5000/passes" 
                                           style="display: inline-block; padding: 12px 30px; color: white; text-decoration: none; font-weight: bold; font-size: 14px;">
                                            View My Passes
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            <p style="color: #999; font-size: 11px; margin: 20px 0 0 0;">
                                Receipt No: {receipt['receipt_number']} | Transaction ID: {receipt['transaction_id']}
                            </p>
                        </td>
                    </tr>
                </table>
                
            </td>
        </tr>
    </table>
    
</body>
</html>
        """
        
        # Send email with HTML attachment
        attachment_filename = f"TSRTC_Pass_{pass_id}.html"
        send_email(user_email, subject, html_body, ticket_html, attachment_filename)
        print(f"✅ TSRTC ticket email sent to {user_email} with HTML attachment")
        
    except Exception as e:
        print(f"❌ Failed to send TSRTC ticket email: {e}")
        raise e

# ---------- START THE APPLICATION ----------
if __name__ == "__main__":
    app.run(host='localhost', port=5000, debug=True)

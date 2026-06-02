from flask import Flask, render_template, request, redirect, url_for, jsonify
import random
import smtplib
from email.mime.text import MIMEText
import os

app = Flask(__name__, template_folder='templates', static_folder='static')

otp_store = {}   # temporary OTP storage (for mini project)

# ---------- HOME ----------
@app.route("/")
def index():
    return render_template("index.html")

# ---------- PASSES PAGE ----------
@app.route("/passes")
def passes():
    return render_template("passes.html")

# ---------- RENEW PASS PAGE ----------
@app.route("/renew-pass")
def renew_pass():
    return render_template("renew-pass.html")

# ---------- RENEW VERIFY PAGE ----------
@app.route("/renew-verify")
def renew_verify():
    email = request.args.get('email')
    if not email:
        return redirect(url_for('renew_pass'))
    return render_template("renew-verify.html", email=email)

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
    SENDER_PASSWORD = "YOUR_NEW_APP_PASSWORD_HERE"  # ⚠️ REPLACE WITH YOUR NEW 16-DIGIT APP PASSWORD
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
    user_otp = request.form["otp"]

    if email in otp_store and str(otp_store[email]) == user_otp:
        # Clear the OTP after successful verification
        del otp_store[email]
        # Redirect to dashboard after successful renewal
        return redirect(url_for('dashboard'))
    else:
        return render_template("renew-verify.html", 
                             email=email, 
                             error="Invalid OTP. Please try again.")

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

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
    SENDER_PASSWORD = "YOUR_NEW_APP_PASSWORD_HERE"  # ⚠️ REPLACE WITH YOUR NEW 16-DIGIT APP PASSWORD
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
        print(f"🔑 Password: YOUR_NEW_APP_PASSWORD_HERE")
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("mk4829779@gmail.com", "YOUR_NEW_APP_PASSWORD_HERE")
        server.quit()
        
        print("✅ Gmail SMTP connection successful!")
        return "<h2>✅ Email configuration is working!</h2><p>Gmail SMTP connection successful.</p>"
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Gmail Authentication Error: {e}")
        return f"<h2>❌ Gmail Authentication Failed</h2><p>Error: {str(e)}</p><p><strong>Solution:</strong> Check your Gmail App Password</p>"
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return f"<h2>❌ Email configuration failed</h2><p>Error: {str(e)}</p><p>Error type: {type(e).__name__}</p>"

if __name__ == "__main__":
    print("🚀 Smart Bus App Starting...")
    print("📧 Email Configuration:")
    print("   - Gmail: mk4829779@gmail.com")
    print("   - App Password: YOUR_NEW_APP_PASSWORD_HERE")
    print("🌐 Access your app at: http://127.0.0.1:5000/passes")
    print("🧪 Test email at: http://127.0.0.1:5000/test-email")
    print("=" * 50)
    app.run(debug=True)
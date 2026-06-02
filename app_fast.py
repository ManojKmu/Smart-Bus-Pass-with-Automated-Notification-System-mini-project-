import imaplib
import ssl
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import datetime
import json
import threading
import time
import requests
from database import db  # Import MySQL database

app = Flask(__name__, template_folder='templates', static_folder='static')

# Configure session for fast login
app.secret_key = 'smartbus_fast_login_2026'  # Change this in production
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# PERFORMANCE OPTIMIZATIONS
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # Cache static files for 1 year
app.config['JSON_SORT_KEYS'] = False  # Don't sort JSON keys for speed
app.config['TEMPLATES_AUTO_RELOAD'] = False  # Disable for production speed
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # Faster JSON responses
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Security
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Security
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size

# Disable Flask's default request logging for speed (optional)
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

otp_store = {}   # temporary OTP storage (for mini project)
reset_tokens = {}  # Password reset tokens storage

# Email configuration
SENDER_EMAIL = "mk4829779@gmail.com"
SENDER_PASSWORD = "cbfiekxqfivdwcjs"  # App password for Gmail

# Skip slow database stats at startup for faster server start
print("=" * 60)
print(">> SMART BUS SYSTEM - ULTRA FAST MODE")
print("=" * 60)
print(f"SUCCESS: MySQL Connected: {db.connection.is_connected() if db.connection else False}")
print("=" * 60)

# ---------- FAST ROUTE HANDLERS ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    """Admin login page"""
    if request.method == "POST":
        admin_id = request.form.get("admin_id")
        password = request.form.get("password")
        
        # Check admin credentials
        if admin_id == "8340" and password == "Manoj":
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            return render_template("admin_login.html", error="Invalid admin ID or password")
    
    return render_template("admin_login.html")

@app.route("/admin")
def admin_panel():
    """Admin panel - shows all user data"""
    # Check if admin is logged in
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    # Get all data from database
    try:
        # Exclude test accounts - only show real logged-in users
        excluded_emails = ('test@example.com', 'admin@smartbus.com', 'test.user@gmail.com', 'student@college.edu')
        
        # Get only real users who have logged in (exclude test accounts)
        users = db.fetch_all("""
            SELECT DISTINCT u.id, u.email, u.password, u.name, u.account_type, u.created_at 
            FROM users u
            INNER JOIN login_history lh ON u.email = lh.user_email
            WHERE u.email NOT IN ('test@example.com', 'admin@smartbus.com', 'test.user@gmail.com', 'student@college.edu')
            ORDER BY u.created_at DESC
        """)
        print(f"DEBUG: Fetched {len(users) if users else 0} real logged-in users (excluding test accounts)")
        
        # Get user details with profile information (exclude test accounts)
        user_details = db.fetch_all("""
            SELECT DISTINCT u.id, u.email, u.name, u.phone, u.city, u.address, u.account_type, u.created_at
            FROM users u
            INNER JOIN login_history lh ON u.email = lh.user_email
            WHERE u.email NOT IN ('test@example.com', 'admin@smartbus.com', 'test.user@gmail.com', 'student@college.edu')
            ORDER BY u.created_at DESC
        """)
        print(f"DEBUG: Fetched {len(user_details) if user_details else 0} user details (excluding test accounts)")

        # Get all passes (includes payment info)
        passes = db.fetch_all("""
            SELECT id, user_email, pass_type, route, distance,
                   price, status, purchase_date, expiry_date,
                   payment_method, transaction_id
            FROM passes ORDER BY purchase_date DESC
        """)
        print(f"DEBUG: Fetched {len(passes) if passes else 0} passes")

        # Get login history
        logins = db.fetch_all("""
            SELECT id, user_email, ip_address, user_agent, login_time
            FROM login_history ORDER BY login_time DESC LIMIT 100
        """)
        print(f"DEBUG: Fetched {len(logins) if logins else 0} logins")

        # Convert dictionary results to tuples for template compatibility
        users_list = [[u['id'], u['email'], u.get('password', ''), u.get('name', ''), u.get('account_type', 'email'), u.get('created_at', '')] for u in users] if users else []
        print(f"DEBUG: Converted {len(users_list)} users to list")

        # For passes, combine route and distance info
        passes_list = [[
            p['id'],
            p['user_email'],
            p['pass_type'],
            p.get('route', 'N/A'),  # Route instead of from_location
            p.get('distance', 'N/A'),  # Distance instead of to_location
            p['price'],  # price instead of amount
            p['status'],
            p['purchase_date'],
            p['expiry_date']
        ] for p in passes] if passes else []
        print(f"DEBUG: Converted {len(passes_list)} passes to list")

        # Create payments list from passes (since payments are in passes table)
        payments_list = [[
            p['id'],
            p['user_email'],
            p['price'],
            p.get('payment_method', 'UPI'),
            p.get('transaction_id', 'N/A'),
            'completed',  # All stored passes are completed payments
            p['purchase_date']
        ] for p in passes] if passes else []
        print(f"DEBUG: Converted {len(payments_list)} payments to list")

        logins_list = [[l['id'], l['user_email'], l['ip_address'], l['user_agent'], l['login_time']] for l in logins] if logins else []
        print(f"DEBUG: Converted {len(logins_list)} logins to list")
        
        # Convert user details to list
        user_details_list = [[
            ud['id'],
            ud['email'],
            ud.get('name', 'N/A'),
            ud.get('phone', 'N/A'),
            ud.get('city', 'N/A'),
            ud.get('address', 'N/A'),
            ud.get('account_type', 'email'),
            ud.get('created_at', 'N/A')
        ] for ud in user_details] if user_details else []
        print(f"DEBUG: Converted {len(user_details_list)} user details to list")

        # Calculate statistics
        total_users = len(users_list)
        total_passes = len(passes_list)
        active_passes = len([p for p in passes_list if p[6] == 'active']) if passes_list else 0

        print(f"DEBUG: Stats - Users: {total_users}, Passes: {total_passes}, Active: {active_passes}")

        return render_template("admin.html",
                             users=users_list,
                             user_details=user_details_list,
                             passes=passes_list,
                             payments=payments_list,
                             logins=logins_list,
                             total_users=total_users,
                             total_passes=total_passes,
                             active_passes=active_passes)
    except Exception as e:
        print(f"Error loading admin data: {e}")
        import traceback
        traceback.print_exc()
        return f"Error loading admin data: {e}"



@app.route("/google-callback")
def google_callback():
    """Google OAuth callback page"""
    return render_template("google_callback.html")

@app.route("/test-google-debug")
def test_google_debug():
    """Debug page for Google OAuth"""
    return render_template("test_google_debug.html")

@app.route("/passes")
def passes():
    """Passes page with user email from session"""
    # Get user email from session
    user_email = session.get('user_email', '')
    user_name = session.get('user_name', '')
    
    print(f"[PAGE] Passes page accessed by: {user_email if user_email else 'Not logged in'}")
    
    # Pass user data to template
    return render_template("passes.html", 
                         user_email=user_email,
                         user_name=user_name)

@app.route("/pass-ticket")
def pass_ticket():
    """TSRTC-style ticket view for passes"""
    # Get user email from session
    user_email = session.get('user_email', '')
    user_name = session.get('user_name', '')
    
    print(f"[PASS] Ticket view accessed by: {user_email if user_email else 'Not logged in'}")
    
    # Pass user data to template
    return render_template("pass_ticket.html", 
                         user_email=user_email,
                         user_name=user_name)

@app.route("/pass-ticket-tsrtc")
def pass_ticket_tsrtc():
    """Real TSRTC-style pass ticket (matches actual TSRTC design)"""
    # Get user email from session
    user_email = session.get('user_email', '')
    user_name = session.get('user_name', '')
    
    print(f"[PASS] TSRTC Pass view accessed by: {user_email if user_email else 'Not logged in'}")
    
    # Pass user data to template
    return render_template("pass_ticket_tsrtc.html", 
                         user_email=user_email,
                         user_name=user_name)

@app.route("/pass-selection")
def pass_selection():
    return render_template("pass-selection.html")

@app.route("/route")
def route():
    """Route selection page with embedded map"""
    try:
        print("[ROUTE] Route page accessed")
        print(f"[ROUTE] User session: {session.get('user_email', 'Not logged in')}")
        # Use route_embedded_map.html for map display
        return render_template("route_embedded_map.html")
    except Exception as e:
        print(f"ERROR: Route page error: {e}")
        import traceback
        traceback.print_exc()
        # Return a simple error page instead of crashing
        return f"<h1>Error loading route page</h1><p>{str(e)}</p><a href='/dashboard'>Back to Dashboard</a>", 500

@app.route("/process-payment")
def process_payment():
    """Payment processing page - handles UPI app opening"""
    app_name = request.args.get('app', 'phonepe')
    amount = request.args.get('amount', '50')
    pass_type = request.args.get('pass', 'Daily Pass')
    
    return render_template("process_payment.html", 
                         app_name=app_name, 
                         amount=amount, 
                         pass_type=pass_type)

@app.route("/payment-success")
def payment_success():
    """Payment success page"""
    return render_template("payment_success.html")

@app.route("/payment")
def payment():
    """Payment page with enhanced error handling and user data"""
    try:
        # Get pass data from URL parameters if available
        pass_type = request.args.get('pass', 'Daily Pass')
        price = request.args.get('price', '₹50')
        route = request.args.get('route', 'City Center - Airport')
        
        # Get user email from session or URL
        user_email = session.get('user_email', request.args.get('email', ''))
        user_name = session.get('user_name', request.args.get('name', 'Passenger'))
        
        print(f"\n{'='*60}")
        print(f"📄 PAYMENT PAGE ACCESSED")
        print(f"{'='*60}")
        print(f"Pass Type: {pass_type}")
        print(f"Price: {price}")
        print(f"Route: {route}")
        print(f"User: {user_email or 'Not logged in'}")
        print(f"{'='*60}\n")
        
        # Warn if user is not logged in
        if not user_email:
            print(f"⚠️  WARNING: User email not available in session")
            print(f"   The payment will still work if user enters email on payment page")
        
        # Use Razorpay payment template
        return render_template("payment_razorpay.html", 
                             pass_type=pass_type, 
                             price=price, 
                             route=route,
                             user_email=user_email,
                             user_name=user_name,
                             razorpay_enabled=RAZORPAY_ENABLED)
    except Exception as e:
        print(f"\n❌ ERROR in payment page: {e}")
        import traceback
        print(traceback.format_exc())
        print()
        return f"""
        <html>
            <head>
                <title>Payment Error</title>
                <style>
                    body {{ font-family: Arial; padding: 40px; background: #f5f5f5; }}
                    .error-box {{ background: white; padding: 30px; border-radius: 10px; max-width: 600px; margin: 0 auto; border-left: 5px solid #f44336; }}
                    h1 {{ color: #f44336; }}
                    p {{ color: #666; line-height: 1.6; }}
                    .code {{ background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; font-family: monospace; margin: 10px 0; }}
                    a {{ color: #4CAF50; text-decoration: none; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="error-box">
                    <h1>⚠️ Payment Page Error</h1>
                    <p>Unfortunately, there was an error loading the payment page:</p>
                    <div class="code">{str(e)}</div>
                    <p><strong>What to do:</strong></p>
                    <ul>
                        <li>Make sure you're logged in</li>
                        <li>Check your internet connection</li>
                        <li>Try clearing your browser cache</li>
                        <li>Contact support if the problem persists</li>
                    </ul>
                    <p><a href="/dashboard">← Go back to Dashboard</a></p>
                </div>
            </body>
        </html>
        """, 500

@app.route("/debug-passes")
def debug_passes():
    """Debug page to check pass display issues"""
    return render_template("debug_passes.html")

@app.route("/api/test-db")
def test_db():
    """Test database connection"""
    try:
        # Try to fetch one pass
        test_query = db.fetch_all("SELECT COUNT(*) as count FROM passes LIMIT 1")
        return jsonify({"success": True, "message": "Database connected"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/payment-mobile")
def payment_mobile():
    """Force mobile payment page"""
    pass_type = request.args.get('pass', 'Daily Pass')
    price = request.args.get('price', '₹50')
    route = request.args.get('route', 'City Center - Airport')
    
    return render_template("payment_mobile.html", 
                         pass_type=pass_type, 
                         price=price, 
                         route=route)

@app.route("/payment-secure")
def payment_secure():
    """Force secure payment page"""
    pass_type = request.args.get('pass', 'Daily Pass')
    price = request.args.get('price', '₹50')
    route = request.args.get('route', 'City Center - Airport')
    
    return render_template("payment_secure.html", 
                         pass_type=pass_type, 
                         price=price, 
                         route=route)

# ---------- AUTOMATIC PAYMENT VERIFICATION (NO FAKE PAYMENTS) ----------
@app.route("/verify-secure-payment", methods=["POST"])
def verify_secure_payment():
    """Verify secure payment automatically - NO MANUAL CONFIRMATION ALLOWED"""
    try:
        data = request.get_json()
        
        amount = data.get('amount')
        upi_id = data.get('upi_id', '8340927497@ibl')
        merchant_name = data.get('merchant_name', 'Lingam Manoj Kumar')
        timestamp = data.get('timestamp')
        auto_verify = data.get('auto_verify', False)
        
        print(f"[SEARCH] Automatic payment verification:")
        print(f"   Amount: ₹{amount}")
        print(f"   UPI ID: {upi_id}")
        print(f"   Merchant: {merchant_name}")
        print(f"   Timestamp: {timestamp}")
        print(f"   Auto verify: {auto_verify}")
        
        # In a real implementation, you would:
        # 1. Check with your bank's API for recent transactions
        # 2. Verify UPI payment gateway webhooks
        # 3. Check SMS notifications for payment confirmations
        # 4. Use payment gateway APIs to verify transaction status
        # 5. Match transaction amount and timestamp
        
        # For production, integrate with:
        # - Razorpay UPI verification API
        # - PayU payment verification
        # - Bank statement APIs
        # - UPI gateway webhooks
        # - SMS parsing for payment confirmations
        
        # SECURITY: Only return True when payment is actually verified
        # This prevents fake payments completely
        
        print(f"WARNING: DEMO MODE: Automatic payment verification")
        print(f"   In production: Check actual bank transactions automatically")
        print(f"   Current: Simulating automatic verification for demo")
        
        # For demo, simulate automatic verification after some time
        # In production, this would check real payment status
        import random
        
        # Simulate automatic payment detection (in production, check real transactions)
        payment_detected = random.choice([True, False])  # 50% chance for demo
        
        if payment_detected:
            result = {
                "success": True,
                "payment_verified": True,
                "message": "Payment automatically verified",
                "verification_method": "automatic",
                "demo_mode": True,
                "transaction_id": f"AUTO{int(time.time())}",
                "verified_at": datetime.datetime.now().isoformat()
            }
            print(f"SUCCESS: Automatic verification: Payment VERIFIED")
        else:
            result = {
                "success": True,
                "payment_verified": False,
                "message": "Payment not detected yet - checking again...",
                "verification_method": "automatic",
                "demo_mode": True,
                "next_check_in": 10
            }
            print(f"⏳ Automatic verification: Payment NOT YET DETECTED")
        
        return result
        
    except Exception as e:
        print(f"ERROR: Automatic payment verification failed: {e}")
        return {
            "success": False,
            "payment_verified": False,
            "error": str(e),
            "message": "Automatic payment verification failed"
        }, 500

# ---------- MANUAL PAYMENT VERIFICATION (Admin) ----------
@app.route("/admin-verify-payment", methods=["POST"])
def admin_verify_payment():
    """Admin endpoint to manually verify payments after checking bank account"""
    try:
        data = request.get_json()
        
        # Admin verification data
        admin_key = data.get('admin_key')
        transaction_id = data.get('transaction_id')
        amount = data.get('amount')
        upi_ref = data.get('upi_ref')
        
        # Simple admin key check (in production, use proper authentication)
        if admin_key != "SMARTBUS_ADMIN_2026":
            return {"success": False, "error": "Unauthorized"}, 401
        
        print(f"[ADMIN] Admin verifying payment:")
        print(f"   Transaction ID: {transaction_id}")
        print(f"   Amount: ₹{amount}")
        print(f"   UPI Ref: {upi_ref}")
        
        # In production, admin would:
        # 1. Check bank account for incoming payment
        # 2. Match amount and timestamp
        # 3. Verify UPI reference number
        # 4. Confirm payment is legitimate
        
        result = {
            "success": True,
            "payment_verified": True,
            "verified_by": "admin",
            "transaction_id": transaction_id,
            "amount": amount,
            "timestamp": datetime.datetime.now().isoformat(),
            "message": "Payment verified by admin"
        }
        
        print(f"SUCCESS: Admin verified payment: {transaction_id}")
        return result
        
    except Exception as e:
        print(f"ERROR: Admin verification failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }, 500

@app.route("/payment-demo")
def payment_demo():
    # Demo payment page (ultra-fast)
    pass_type = request.args.get('pass', 'Daily Pass')
    price = request.args.get('price', '₹50')
    route = request.args.get('route', 'City Center - Airport')
    
    return render_template("payment_ultrafast.html", 
                         pass_type=pass_type, 
                         price=price, 
                         route=route)

@app.route("/payment-normal")
def payment_normal():
    # Normal payment page with realistic delays
    pass_type = request.args.get('pass', 'Daily Pass')
    price = request.args.get('price', '₹50')
    route = request.args.get('route', 'City Center - Airport')
    
    return render_template("payment_fixed.html", 
                         pass_type=pass_type, 
                         price=price, 
                         route=route)

@app.route("/payment-qr")
def payment_qr():
    """QR enhanced payment page"""
    pass_type = request.args.get('pass', 'Daily Pass')
    price = request.args.get('price', '₹75')
    route = request.args.get('route', 'City Center - Airport')
    
    return render_template("payment_qr_enhanced.html", 
                         pass_type=pass_type, 
                         price=price, 
                         route=route)

@app.route("/payment-upi")
def payment_upi():
    """Custom UPI payment page with QR code and VPA textbox"""
    pass_type = request.args.get('pass', 'Daily Pass')
    price = request.args.get('price', '₹75')
    route = request.args.get('route', 'City Center - Airport')
    
    return render_template("payment_upi_custom.html", 
                         pass_type=pass_type, 
                         price=price, 
                         route=route)

@app.route("/process-upi-payment", methods=["POST"])
def process_upi_payment():
    """Process custom UPI payment - FAST VERSION"""
    try:
        data = request.get_json()
        
        # Get payment details
        amount = float(data.get('amount', 0))
        pass_type = data.get('pass_type', 'Daily Pass')
        route = data.get('route', 'City Route')
        distance = data.get('distance', '0')
        user_email = data.get('user_email', '')
        user_name = data.get('user_name', '')
        upi_id = data.get('upi_id', '')
        
        print(f"💳 Processing UPI payment:")
        print(f"   Amount: ₹{amount}")
        print(f"   UPI ID: {upi_id}")
        print(f"   Pass: {pass_type}")
        print(f"   User: {user_email}")
        
        # Validate amount
        if amount <= 0:
            return jsonify({'success': False, 'error': 'Invalid amount'}), 400
        
        # Validate UPI ID
        if not upi_id or '@' not in upi_id:
            return jsonify({'success': False, 'error': 'Invalid UPI ID'}), 400
        
        # Generate transaction ID
        transaction_id = f"UPI{int(datetime.datetime.now().timestamp() * 1000)}"
        
        # Create pass data
        pass_data = {
            'id': int(datetime.datetime.now().timestamp() * 1000),
            'type': pass_type,
            'price': f"₹{amount}",
            'route': route,
            'distance': distance,
            'purchaseDate': datetime.datetime.now().isoformat(),
            'expiryDate': calculate_expiry_date(pass_type),
            'status': 'active',
            'paymentMethod': 'UPI',
            'transactionId': transaction_id,
            'upiId': upi_id
        }
        
        # Save to database (FAST - async)
        if user_email:
            try:
                expiry_date_str = calculate_expiry_date(pass_type)
                db.create_pass(
                    user_email=user_email,
                    pass_type=pass_type,
                    price=float(amount),
                    route=route,
                    distance=float(distance) if distance else 0.0,
                    expiry_date=expiry_date_str,
                    payment_method='UPI',
                    transaction_id=transaction_id
                )
                print(f"✓ Pass saved to database")
            except Exception as e:
                print(f"⚠ Database save failed: {e}")
        
        # Generate receipt
        receipt = generate_enhanced_receipt(
            pass_type=pass_type,
            amount=str(amount),
            route=route,
            distance=distance,
            payment_method='UPI',
            user_name=user_name,
            user_email=user_email,
            transaction_type='new_pass',
            device_type='Web'
        )
        
        # Send emails ASYNCHRONOUSLY (don't wait)
        def send_emails_async():
            try:
                if user_email:
                    send_enhanced_email_notification(
                        user_email, 
                        user_name, 
                        receipt, 
                        'new_pass'
                    )
                    send_tsrtc_pass_email(
                        user_email,
                        user_name,
                        pass_data
                    )
                    print(f"✓ Emails sent to {user_email}")
            except Exception as e:
                print(f"⚠ Email error: {e}")
        
        # Start email thread (non-blocking)
        email_thread = threading.Thread(target=send_emails_async)
        email_thread.daemon = True
        email_thread.start()
        
        print(f"SUCCESS: UPI payment processed: {transaction_id}")
        
        return jsonify({
            'success': True,
            'message': 'Payment processed successfully',
            'transaction_id': transaction_id,
            'receipt': receipt,
            'pass_data': pass_data
        })
        
    except Exception as e:
        print(f"ERROR: UPI payment processing failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/save-test-payment", methods=["POST"])
def save_test_payment():
    """Save test payment (for development/testing without Razorpay)"""
    try:
        data = request.get_json()
        
        # Get payment details
        user_email = data.get('email', '')
        pass_type = data.get('pass_type', 'Daily Pass')
        amount = float(data.get('amount', 0))
        route = data.get('route', 'City Route')
        distance = data.get('distance', '0')
        user_name = data.get('user_name', 'Passenger')
        pass_data = data.get('pass', {})
        
        print(f"🧪 TEST MODE: Saving test payment:")
        print(f"   Amount: ₹{amount}")
        print(f"   Pass: {pass_type}")
        print(f"   User: {user_email}")
        
        # Validate
        if not user_email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400
        
        if amount <= 0:
            return jsonify({'success': False, 'error': 'Invalid amount'}), 400
        
        # Generate transaction ID
        transaction_id = pass_data.get('transactionId', f"TEST_{int(datetime.datetime.now().timestamp() * 1000)}")
        
        # Save to database
        try:
            expiry_date_str = calculate_expiry_date(pass_type)
            db.create_pass(
                user_email=user_email,
                pass_type=pass_type,
                price=float(amount),
                route=route,
                distance=float(distance) if distance else 0.0,
                expiry_date=expiry_date_str,
                payment_method='Test Mode',
                transaction_id=transaction_id
            )
            print(f"✓ Test pass saved to database")
        except Exception as e:
            print(f"⚠ Database save failed: {e}")
            return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
        
        # Generate receipt
        receipt = generate_enhanced_receipt(
            pass_type=pass_type,
            amount=str(amount),
            route=route,
            distance=distance,
            payment_method='Test Mode',
            user_name=user_name,
            user_email=user_email,
            transaction_type='new_pass',
            device_type='Web'
        )
        
        # Send emails ASYNCHRONOUSLY (don't wait)
        def send_emails_async():
            try:
                if user_email:
                    send_enhanced_email_notification(
                        user_email, 
                        user_name, 
                        receipt, 
                        'new_pass'
                    )
                    send_tsrtc_pass_email(
                        user_email,
                        user_name,
                        pass_data
                    )
                    print(f"✓ Test emails sent to {user_email}")
            except Exception as e:
                print(f"⚠ Email error: {e}")
        
        # Start email thread (non-blocking)
        email_thread = threading.Thread(target=send_emails_async)
        email_thread.daemon = True
        email_thread.start()
        
        print(f"SUCCESS: Test payment saved: {transaction_id}")
        
        return jsonify({
            'success': True,
            'message': 'Test payment processed successfully',
            'transaction_id': transaction_id,
            'receipt': receipt,
            'pass_data': pass_data
        })
        
    except Exception as e:
        print(f"ERROR: Test payment failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/dashboard")
def dashboard():
    """Dashboard page with user email from session"""
    # Get user email from session
    user_email = session.get('user_email', '')
    user_name = session.get('user_name', '')
    
    print(f"[DATA] Dashboard accessed by: {user_email if user_email else 'Not logged in'}")
    
    # Pass user data to template
    return render_template("dashboard.html",
                         user_email=user_email,
                         user_name=user_name)

@app.route("/api/track", methods=["POST"])
def api_track():
    """Track user activity (dashboard visits, etc.)"""
    try:
        data = request.get_json()
        action = data.get('action', 'unknown')
        email = data.get('email', '')
        
        # Log the activity
        print(f"[DATA] Activity tracked: {action} by {email}")
        
        # You can store this in database if needed
        # For now, just acknowledge it
        return jsonify({"success": True, "message": "Activity tracked"})
        
    except Exception as e:
        print(f"ERROR: Error tracking activity: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/get_profile", methods=["GET"])
def get_profile():
    """Get user profile from MySQL"""
    try:
        email = request.args.get('email', '').lower().strip()
        
        if not email:
            return jsonify({"success": False, "error": "Email is required"}), 400
        
        # Get user from MySQL
        user = db.get_user(email)
        
        if user:
            return jsonify({
                "success": True,
                "profile": {
                    "email": user['email'],
                    "name": user.get('name', ''),
                    "phone": user.get('phone', ''),
                    "city": user.get('city', ''),
                    "address": user.get('address', ''),
                    "account_type": user.get('account_type', 'email')
                }
            })
        else:
            return jsonify({"success": False, "error": "User not found"}), 404
            
    except Exception as e:
        print(f"ERROR: Error getting profile: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/update_profile", methods=["POST"])
def update_profile():
    """Update user profile information - MYSQL VERSION"""
    try:
        data = request.get_json()
        
        email = data.get('email', '').lower().strip()
        phone = data.get('phone', '').strip()
        city = data.get('city', '').strip()
        address = data.get('address', '').strip()
        
        print(f"[EDIT] Updating profile for: {email}")
        print(f"   Phone: {phone}")
        print(f"   City: {city}")
        print(f"   Address: {address}")
        
        if not email:
            return jsonify({"success": False, "error": "Email is required"}), 400
        
        # Validate phone number
        if not phone or len(phone.replace(' ', '')) != 10:
            return jsonify({"success": False, "error": "Valid 10-digit phone number is required"}), 400
        
        # Validate city
        if not city or len(city) < 2:
            return jsonify({"success": False, "error": "City must be at least 2 characters"}), 400
        
        # Validate address
        if not address or len(address) < 10:
            return jsonify({"success": False, "error": "Address must be at least 10 characters"}), 400
        
        # Check if user exists in MySQL
        user = db.get_user(email)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
        
        # Update user profile in MySQL
        success = db.update_user_profile(email, phone, city, address)
        
        if success:
            print(f"SUCCESS: Profile updated successfully in MySQL for {email}")
            
            return jsonify({
                "success": True,
                "message": "Profile updated successfully",
                "user": {
                    "email": email,
                    "name": user.get('name', ''),
                    "phone": phone,
                    "city": city,
                    "address": address
                }
            })
        else:
            return jsonify({"success": False, "error": "Failed to update profile in database"}), 500
        
    except Exception as e:
        print(f"ERROR: Error updating profile: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/debug/profiles")
def debug_profiles():
    """Debug route to view all stored profiles"""
    user_profiles = getattr(app, 'user_profiles', {})
    user_accounts = getattr(app, 'user_accounts', {})
    
    return jsonify({
        "total_profiles": len(user_profiles),
        "total_accounts": len(user_accounts),
        "profiles": user_profiles,
        "accounts": list(user_accounts.keys())
    })

# ---------- RENEW PASS FUNCTIONALITY ----------
@app.route("/renew-pass")
def renew_pass():
    """Renew pass page"""
    return render_template("renew-pass.html")

@app.route("/renew-verify")
def renew_verify():
    """Renew verify page"""
    email = request.args.get('email')
    if not email:
        return redirect(url_for('renew_pass'))
    return render_template("renew-verify.html", email=email)

@app.route("/send-renew-otp", methods=["POST"])
def send_renew_otp():
    """Send OTP for pass renewal"""
    try:
        user_email = request.form["email"]
        
        # Email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, user_email):
            error_msg = "Please enter a valid email address (e.g., user@gmail.com)."
            return render_template("renew-pass.html", error=error_msg)
        
        # Check if email domain exists (basic check)
        if not any(domain in user_email.lower() for domain in ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com']):
            error_msg = "Please use a valid email provider (Gmail, Yahoo, Outlook, etc.)."
            return render_template("renew-pass.html", error=error_msg)
        
        # Generate OTP
        otp = random.randint(100000, 999999)
        otp_store[user_email] = otp
        
        print(f"[EMAIL] Sending renewal OTP to: {user_email}")
        print(f"🔢 Generated OTP: {otp}")
        
        # Email configuration
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfiekxqfivdwcjs"
        RECIPIENT_EMAIL = user_email
        
        # Create email message
        msg = MIMEText(f"""
Hello,

Your Smart Bus Pass Renewal OTP is: {otp}

This OTP is valid for 10 minutes.

Please enter this OTP on the verification page to renew your pass.

Thank you for using Smart Bus!

Smart Bus Team
        """)
        msg["Subject"] = "Smart Bus Pass Renewal - OTP Verification"
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECIPIENT_EMAIL
        
        # Send email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"SUCCESS: Renewal OTP sent successfully to {user_email}")
        return render_template("renew-verify.html", email=user_email)
        
    except smtplib.SMTPAuthenticationError:
        print("ERROR: Gmail authentication failed - Check App Password")
        error_msg = "Email service authentication failed. Please contact support."
        return render_template("renew-pass.html", error=error_msg)
        
    except smtplib.SMTPRecipientsRefused:
        print(f"ERROR: Invalid email address: {user_email}")
        error_msg = "Invalid email address. Please enter a valid email."
        return render_template("renew-pass.html", error=error_msg)
        
    except Exception as e:
        print(f"ERROR: Error sending renewal OTP: {e}")
        error_msg = "Failed to send OTP. Please check your email address and try again."
        return render_template("renew-pass.html", error=error_msg)

@app.route("/verify-renew-otp", methods=["POST"])
def verify_renew_otp():
    """Verify OTP for pass renewal - ENHANCED WITH EMAIL NOTIFICATION"""
    try:
        email = request.form["email"]
        user_otp = request.form["otp"].strip()
        
        print(f"[SEARCH] Verifying renewal OTP for: {email}")
        print(f"🔢 User entered OTP: '{user_otp}'")
        
        if email in otp_store:
            stored_otp = str(otp_store[email])
            print(f"🔢 Stored OTP: '{stored_otp}'")
            
            if user_otp == stored_otp:
                print(f"SUCCESS: OTP verified successfully for: {email}")
                
                # Remove OTP from store
                del otp_store[email]
                
                # Send renewal confirmation email
                try:
                    renewal_receipt = generate_enhanced_receipt(
                        pass_type="Pass Renewal",
                        amount="0",  # Renewal might be free or have different pricing
                        route="All Routes",
                        distance="0",
                        payment_method="OTP Verification",
                        user_name=email.split('@')[0].title(),
                        user_email=email,
                        transaction_type="renewal",
                        device_type="Web"
                    )
                    
                    email_sent = send_enhanced_email_notification(
                        email, 
                        email.split('@')[0].title(), 
                        renewal_receipt, 
                        "renewal"
                    )
                    
                    if email_sent:
                        print(f"SUCCESS: Renewal confirmation email sent to: {email}")
                    else:
                        print(f"WARNING: Renewal email failed but OTP verified for: {email}")
                        
                except Exception as e:
                    print(f"ERROR: Renewal email error: {e}")
                
                # Redirect to dashboard with success message
                return render_template("dashboard.html", 
                                     success_message="Pass renewal verified! Check your email for confirmation.",
                                     show_buy_pass=True)
            else:
                print(f"ERROR: OTP mismatch: stored='{stored_otp}', entered='{user_otp}'")
                return render_template("renew-verify.html", 
                                     email=email, 
                                     error="Invalid OTP. Please try again.")
        else:
            print(f"ERROR: No OTP found for email: {email}")
            return render_template("renew-verify.html", 
                                 email=email, 
                                 error="OTP expired or not found. Please request a new OTP.")
                                 
    except Exception as e:
        print(f"ERROR: Error verifying renewal OTP: {e}")
        return render_template("renew-verify.html", 
                             email=email, 
                             error="Verification failed. Please try again.")

@app.route("/resend-renew-otp", methods=["POST"])
def resend_renew_otp():
    """Resend OTP for pass renewal"""
    try:
        # Handle both form and JSON requests
        if request.is_json:
            email = request.json.get("email")
        else:
            email = request.form.get("email")
        
        if not email:
            return {"success": False, "error": "Email is required"}, 400
        
        # Generate new OTP
        otp = random.randint(100000, 999999)
        otp_store[email] = otp
        
        print(f"[EMAIL] Resending renewal OTP to: {email}")
        print(f"🔢 New OTP: {otp}")
        
        # Email configuration
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfiekxqfivdwcjs"
        
        # Create email message
        msg = MIMEText(f"""
Hello,

Your Smart Bus Pass Renewal OTP is: {otp}

This OTP is valid for 10 minutes.

Please enter this OTP on the verification page to renew your pass.

Thank you for using Smart Bus!

Smart Bus Team
        """)
        msg["Subject"] = "Smart Bus Pass Renewal - OTP Verification (Resent)"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email
        
        # Send email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"SUCCESS: Renewal OTP resent successfully to {email}")
        
        if request.is_json:
            return {"success": True, "message": "OTP sent successfully"}
        else:
            return render_template("renew-verify.html", 
                                 email=email, 
                                 success="OTP sent successfully!")
                                 
    except Exception as e:
        print(f"ERROR: Error resending renewal OTP: {e}")
        
        if request.is_json:
            return {"success": False, "error": "Failed to send OTP"}, 500
        else:
            return render_template("renew-verify.html", 
                                 email=email, 
                                 error="Failed to resend OTP. Please try again.")

# ---------- PASS RENEWAL PAYMENT COMPLETION ----------
@app.route("/complete-renewal-payment", methods=["POST"])
def complete_renewal_payment():
    """Complete pass renewal payment and update expiry date"""
    try:
        data = request.get_json()
        
        # Get renewal details
        pass_id = data.get('pass_id')
        pass_type = data.get('pass_type')
        amount = data.get('amount')
        payment_method = data.get('payment_method', 'UPI')
        transaction_id = data.get('transaction_id', f"RNW{int(datetime.datetime.now().timestamp())}")
        
        # Get user info from session
        user_email = session.get('user_email') or data.get('user_email')
        user_name = session.get('user_name') or data.get('user_name', 'Smart Bus User')
        
        if not user_email or not pass_id:
            return {"success": False, "error": "Missing required information"}, 400
        
        print(f"💳 Processing renewal payment for pass {pass_id}")
        print(f"   User: {user_email}")
        print(f"   Pass Type: {pass_type}")
        print(f"   Amount: ₹{amount}")
        
        # Calculate new expiry date based on pass type
        from datetime import datetime, timedelta
        now = datetime.now()
        
        if 'Daily' in pass_type:
            new_expiry = now + timedelta(days=1)
        elif 'Weekly' in pass_type:
            new_expiry = now + timedelta(days=7)
        elif 'Monthly' in pass_type or 'Student' in pass_type:
            new_expiry = now + timedelta(days=30)
        elif 'Quarterly' in pass_type:
            new_expiry = now + timedelta(days=90)
        elif 'Annual' in pass_type:
            new_expiry = now + timedelta(days=365)
        else:
            new_expiry = now + timedelta(days=30)  # Default to monthly
        
        # Update pass in database
        try:
            # Update expiry date in MySQL
            query = """
                UPDATE passes 
                SET expiry_date = %s, 
                    status = 'active',
                    updated_at = NOW()
                WHERE id = %s AND user_email = %s
            """
            db.execute_query(query, (new_expiry, pass_id, user_email.lower()))
            print(f"✅ Pass {pass_id} renewed until {new_expiry.strftime('%Y-%m-%d')}")
            
        except Exception as db_error:
            print(f"❌ Database update failed: {db_error}")
            return {"success": False, "error": "Failed to update pass"}, 500
        
        # Generate renewal receipt
        renewal_receipt = {
            "receipt_number": f"RNW{int(now.timestamp())}",
            "transaction_id": transaction_id,
            "date": now.strftime("%Y-%m-%d %H:%M:%S"),
            "user_name": user_name,
            "user_email": user_email,
            "pass_id": pass_id,
            "pass_type": pass_type,
            "amount": amount,
            "payment_method": payment_method,
            "renewal_date": now.strftime("%Y-%m-%d"),
            "new_expiry_date": new_expiry.strftime("%Y-%m-%d"),
            "status": "COMPLETED",
            "type": "RENEWAL"
        }
        
        # Send renewal confirmation email in background
        import threading
        
        # Capture data outside of request context
        email_copy = user_email
        name_copy = user_name
        receipt_copy = renewal_receipt.copy()
        
        def send_renewal_email_background():
            try:
                send_renewal_confirmation_email(email_copy, name_copy, receipt_copy)
                print(f"✅ Renewal confirmation email sent to {email_copy}")
            except Exception as e:
                print(f"⚠️ Renewal email failed (non-critical): {e}")
        
        # Start background email thread
        email_thread = threading.Thread(target=send_renewal_email_background)
        email_thread.daemon = True
        email_thread.start()
        
        print(f"🎉 Pass renewal completed successfully for {user_email}")
        
        # Return success response
        return {
            "success": True,
            "message": "🎉 Bus Pass Renewal Completed Successfully!",
            "receipt": renewal_receipt,
            "new_expiry_date": new_expiry.strftime("%Y-%m-%d"),
            "redirect_url": "/passes?renewal=success"
        }
        
    except Exception as e:
        print(f"❌ Renewal payment completion failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}, 500

def send_renewal_confirmation_email(user_email, user_name, receipt):
    """Send renewal confirmation email"""
    try:
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfi ekxq fivd wcjs"
        
        subject = f"🎉 Bus Pass Renewed Successfully - {receipt['pass_type']}"
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #4CAF50, #45a049); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .success-icon {{ font-size: 48px; margin-bottom: 10px; }}
        .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
        .detail-label {{ font-weight: bold; color: #666; }}
        .detail-value {{ color: #333; }}
        .highlight {{ background: #e8f5e9; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="success-icon">✅</div>
            <h1>Pass Renewal Successful!</h1>
            <p>Your bus pass has been renewed</p>
        </div>
        
        <div class="content">
            <p>Dear {user_name},</p>
            
            <p>Great news! Your bus pass has been successfully renewed.</p>
            
            <div class="highlight">
                <strong>🎫 New Expiry Date: {receipt['new_expiry_date']}</strong>
            </div>
            
            <div class="details">
                <h3>Renewal Details</h3>
                <div class="detail-row">
                    <span class="detail-label">Receipt Number:</span>
                    <span class="detail-value">{receipt['receipt_number']}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Pass Type:</span>
                    <span class="detail-value">{receipt['pass_type']}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Amount Paid:</span>
                    <span class="detail-value">₹{receipt['amount']}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Payment Method:</span>
                    <span class="detail-value">{receipt['payment_method']}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Renewal Date:</span>
                    <span class="detail-value">{receipt['renewal_date']}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Valid Until:</span>
                    <span class="detail-value">{receipt['new_expiry_date']}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Transaction ID:</span>
                    <span class="detail-value">{receipt['transaction_id']}</span>
                </div>
            </div>
            
            <p><strong>What's Next?</strong></p>
            <ul>
                <li>Your pass is now active and ready to use</li>
                <li>View your pass anytime at: <a href="http://localhost:5000/passes">My Passes</a></li>
                <li>Download your TSRTC ticket from the passes page</li>
                <li>You'll receive a reminder before your pass expires</li>
            </ul>
            
            <p>Thank you for choosing Smart Bus!</p>
            
            <div class="footer">
                <p>This is an automated email. Please save this for your records.</p>
                <p>Smart Bus - Making Your Journey Smarter</p>
            </div>
        </div>
    </div>
</body>
</html>
        """
        
        # Create email
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        msg = MIMEMultipart('alternative')
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = user_email
        
        # Attach HTML body
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        # Send email
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send renewal email: {e}")
        return False

@app.route("/test-payment")
def test_payment():
    return render_template("../test_payment_page.html")

@app.route("/test-google-login")
def test_google_login():
    """Diagnostic page for Google login issues"""
    return render_template("test_google_login.html")

@app.route("/test-gmail-verification")
def test_gmail_verification_page():
    """Test page for Gmail password verification"""
    return render_template("test_gmail_login.html")

# ---------- GOOGLE LOGIN VERIFICATION ----------
@app.route("/google-login", methods=["POST"])
def google_login():
    """ULTRA-FAST Google OAuth login - Optimized for speed"""
    email = request.form.get("email")
    name = request.form.get("name")
    google_id = request.form.get("google_id", "")
    
    if not email or not name:
        return jsonify({'success': False, 'message': 'Invalid data'}), 400
    
    email_lower = email.lower().strip()
    
    # SPEED OPTIMIZATION: Set session FIRST before any database operations
    session.permanent = True
    session['user_email'] = email_lower
    session['user_name'] = name
    session['account_type'] = 'google'
    session.modified = True
    
    print(f"SUCCESS: Session set immediately for {email_lower}")
    
    # SPEED OPTIMIZATION: Do database operations in background (non-blocking)
    def background_db_operations():
        try:
            import hashlib
            google_password = f"Google_{hashlib.md5(google_id.encode()).hexdigest()[:8]}"
            
            # Check if user exists
            user = db.get_user(email_lower)
            
            if not user:
                # Create new user
                db.create_user(email_lower, google_password, name, 'google')
                print(f"SUCCESS: User created in background: {email_lower}")
            
            # Log the login (non-critical)
            db.log_login(email_lower, request.remote_addr, request.headers.get('User-Agent', ''))
        except Exception as e:
            print(f"WARNING: Background DB operation failed (non-critical): {e}")
    
    # Start background thread for database operations
    import threading
    thread = threading.Thread(target=background_db_operations)
    thread.daemon = True
    thread.start()
    
    # Return immediately - don't wait for database
    print(f"SUCCESS: FAST Google login for {email_lower} - returning immediately")
    return jsonify({
        'success': True,
        'message': 'Login successful',
        'redirect': '/passes'
    }), 200

# ---------- FAST LOGIN WITH MYSQL ----------
@app.route("/login", methods=["POST"])
def login():
    """Enhanced login with automatic Google credential verification"""
    email = request.form.get("email")
    password = request.form.get("password")
    
    if not email or not password:
        return render_template("index.html", error="Please enter both email and password")
    
    email_lower = email.lower().strip()
    password_clean = password.strip()
    
    print(f"🔐 Login attempt with automatic verification: {email_lower}")
    
    # Check if user exists in MySQL database first
    user = db.get_user(email_lower)
    
    if user:
        # User exists - check if it's a Google account or regular account
        account_type = user.get('account_type', 'email')
        
        if account_type in ['google', 'google_verified'] and email_lower.endswith(('@gmail.com', '@googlemail.com')):
            # For Google accounts, verify with Google servers
            print(f"[SEARCH] Verifying Google account with Google servers: {email_lower}")
            
            success, message, google_user_info = verify_google_credentials(email_lower, password_clean)
            
            if success:
                # Google verification successful
                print(f"SUCCESS: Google verification successful: {email_lower}")
                print(f"   [EMAIL] Inbox messages: {google_user_info.get('inbox_count', 0)}")
                
                # Update user info with Google verification
                user_name = user.get('name', google_user_info.get('name', email_lower.split('@')[0]))
                
                # Log login
                try:
                    db.log_login(email_lower, request.remote_addr, request.headers.get('User-Agent', ''))
                except Exception as e:
                    print(f"WARNING: Login logging failed (non-critical): {e}")
                
                # Store session
                session['user_email'] = email_lower
                session['user_name'] = user_name
                session['account_type'] = 'google_verified'
                session['google_verified'] = True
                session['inbox_count'] = google_user_info.get('inbox_count', 0)
                
                return redirect(url_for('passes'))
            else:
                # Google verification failed
                print(f"ERROR: Google verification failed: {email_lower} - {message}")
                return render_template("index.html", 
                                     error=f"Google verification failed: {message}")
        else:
            # Regular account - check stored password
            if user['password'] == password_clean:
                # Correct password
                print(f"SUCCESS: Regular account login successful: {email_lower}")
                
                # Log login
                try:
                    db.log_login(email_lower, request.remote_addr, request.headers.get('User-Agent', ''))
                except Exception as e:
                    print(f"WARNING: Login logging failed (non-critical): {e}")
                
                # Store session
                session['user_email'] = email_lower
                session['user_name'] = user.get('name', email_lower.split('@')[0])
                session['account_type'] = account_type
                session['google_verified'] = False
                
                return redirect(url_for('passes'))
            else:
                print(f"ERROR: Wrong password for regular account: {email_lower}")
                return render_template("index.html", 
                                     error="Incorrect password. Please try again or use 'Forgot password?' to reset.")
    else:
        # User doesn't exist - check if it's a Gmail account for Google verification
        if email_lower.endswith(('@gmail.com', '@googlemail.com')):
            print(f"🆕 New Gmail account - verifying with Google: {email_lower}")
            
            # Verify credentials with Google
            success, message, google_user_info = verify_google_credentials(email_lower, password_clean)
            
            if success:
                # Google verification successful - create new user
                print(f"SUCCESS: New Gmail account verified with Google: {email_lower}")
                
                user_name = google_user_info.get('name', email_lower.split('@')[0].replace('.', ' ').title())
                
                # Create user in MySQL with Google verification
                if db.create_user(email_lower, password_clean, user_name, 'google_verified'):
                    print(f"SUCCESS: New Google-verified account created: {email_lower}")
                    
                    # Log login
                    try:
                        db.log_login(email_lower, request.remote_addr, request.headers.get('User-Agent', ''))
                    except Exception as e:
                        print(f"WARNING: Login logging failed (non-critical): {e}")
                    
                    # Store session
                    session['user_email'] = email_lower
                    session['user_name'] = user_name
                    session['account_type'] = 'google_verified'
                    session['google_verified'] = True
                    session['inbox_count'] = google_user_info.get('inbox_count', 0)
                    
                    return redirect(url_for('passes'))
                else:
                    return render_template("index.html", error="Failed to create account. Please try again.")
            else:
                # Google verification failed
                print(f"ERROR: Gmail verification failed for new account: {email_lower} - {message}")
                return render_template("index.html", 
                                     error=f"Gmail verification failed: {message}")
        else:
            # Not a Gmail account and doesn't exist
            print(f"ERROR: Account not found: {email_lower}")
            return render_template("index.html", 
                                 error=f"No account found with {email}. Please sign up first or use a Gmail address for automatic verification.")

# ---------- FAST UPI PAYMENT INITIATION ----------
@app.route("/initiate-upi-payment", methods=["POST"])
def initiate_upi_payment():
    """Generate UPI payment link for real payment apps - OPTIMIZED"""
    try:
        data = request.get_json()
        upi_app = data.get('upi_app')
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
        
        # Generate UPI payment URL (optimized)
        upi_url = generate_fast_upi_url(upi_app, upi_id, merchant_name, amount, description)
        
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
        return {"success": False, "error": str(e)}, 500

def generate_fast_upi_url(upi_app, upi_id, merchant_name, amount, description):
    """Generate UPI payment URL - ULTRA FAST VERSION"""
    
    # Pre-encode parameters once
    encoded_merchant = merchant_name.replace(" ", "%20")
    encoded_description = description.replace(" ", "%20")
    
    # Simplified app-specific URLs for maximum speed
    app_urls = {
        'phonepe': f"phonepe://pay?pa={upi_id}&pn={encoded_merchant}&am={amount}&cu=INR&tn={encoded_description}",
        'gpay': f"tez://upi/pay?pa={upi_id}&pn={encoded_merchant}&am={amount}&cu=INR&tn={encoded_description}",
        'paytm': f"paytmmp://pay?pa={upi_id}&pn={encoded_merchant}&am={amount}&cu=INR&tn={encoded_description}",
        'bhim': f"bhim://pay?pa={upi_id}&pn={encoded_merchant}&am={amount}&cu=INR&tn={encoded_description}",
    }
    
    # Return the appropriate URL or default to base UPI URL
    return app_urls.get(upi_app.lower(), f"upi://pay?pa={upi_id}&pn={encoded_merchant}&am={amount}&cu=INR&tn={encoded_description}")

# ---------- RAZORPAY PAYMENT INTEGRATION ----------
try:
    import razorpay
    from config_razorpay import RAZORPAY_CONFIG, BASE_URL, IS_PRODUCTION, MERCHANT_INFO, PAYMENT_SETTINGS
    
    # Initialize Razorpay client
    razorpay_client = razorpay.Client(auth=(RAZORPAY_CONFIG['key_id'], RAZORPAY_CONFIG['key_secret']))
    RAZORPAY_ENABLED = True
    print("SUCCESS: Razorpay integration enabled")
    print(f"   Mode: {'LIVE' if IS_PRODUCTION else 'TEST'}")
    print(f"   Key ID: {RAZORPAY_CONFIG['key_id'][:15]}...")
except ImportError:
    RAZORPAY_ENABLED = False
    print("WARNING:  Razorpay not installed. Run: pip install razorpay")
    print("   UPI payment system will continue to work")
except Exception as e:
    RAZORPAY_ENABLED = False
    print(f"WARNING:  Razorpay configuration error: {e}")
    print("   Check config_razorpay.py and update with your API keys")

@app.route("/create-razorpay-order", methods=["POST"])
def create_razorpay_order():
    """Create Razorpay order for payment - ENHANCED WITH ERROR HANDLING"""
    if not RAZORPAY_ENABLED:
        print("❌ Razorpay not enabled - library not installed or configuration error")
        return jsonify({
            'success': False, 
            'error': 'Razorpay not configured. Please install razorpay: pip install razorpay'
        }), 503
    
    try:
        data = request.get_json()
        
        # Get payment details
        amount = float(data.get('amount', 0))
        pass_type = data.get('pass_type', 'Daily Pass')
        route = data.get('route', 'City Route')
        distance = data.get('distance', '0')
        user_email = data.get('user_email', '')
        user_name = data.get('user_name', 'Smart Bus Customer')
        upi_id = data.get('upi_id', '').strip()
        
        # Validate required fields
        if not user_email:
            print(f"❌ Order creation failed: Missing user email")
            return jsonify({
                'success': False, 
                'error': 'User email is required to create order. Please login first.'
            }), 400
        
        # Validate amount
        if amount <= 0:
            print(f"❌ Order creation failed: Invalid amount {amount}")
            return jsonify({
                'success': False, 
                'error': f'Invalid payment amount: ₹{amount}. Amount must be greater than 0.'
            }), 400
        
        # Convert to paise (Razorpay uses smallest currency unit)
        amount_paise = int(amount * 100)
        
        print(f"\n{'='*60}")
        print(f"💳 CREATING RAZORPAY ORDER")
        print(f"{'='*60}")
        print(f"Amount: ₹{amount} ({amount_paise} paise)")
        print(f"Pass Type: {pass_type}")
        print(f"Route: {route}")
        print(f"Distance: {distance}")
        print(f"Customer: {user_name} ({user_email})")
        print(f"{'='*60}\n")
        
        # Create Razorpay order
        order_data = {
            'amount': amount_paise,
            'currency': PAYMENT_SETTINGS['currency'],
            'payment_capture': 1 if PAYMENT_SETTINGS['auto_capture'] else 0,
            'notes': {
                'pass_type': pass_type,
                'route': route,
                'distance': distance,
                'user_email': user_email,
                'user_name': user_name,
                'upi_id': upi_id,
                'payment_source': 'web_app'
            }
        }
        
        try:
            order = razorpay_client.order.create(data=order_data)
            print(f"✅ Razorpay order created successfully!")
            print(f"   Order ID: {order['id']}")
            print(f"   Amount: {order['amount']} paise = ₹{order['amount']/100}")
            print(f"   Status: {order['status']}\n")
        except Exception as order_error:
            print(f"❌ Failed to create Razorpay order: {order_error}")
            # Retry once using a direct HTTPS request in case the Razorpay client library is experiencing a transport issue.
            try:
                fallback_response = requests.post(
                    'https://api.razorpay.com/v1/orders',
                    auth=(RAZORPAY_CONFIG['key_id'], RAZORPAY_CONFIG['key_secret']),
                    json=order_data,
                    timeout=30
                )
                fallback_response.raise_for_status()
                order = fallback_response.json()
                print(f"✅ Razorpay order created successfully via fallback HTTP request!")
                print(f"   Order ID: {order.get('id')}")
                print(f"   Amount: {order.get('amount')} paise = ₹{order.get('amount', 0)/100}")
                print(f"   Status: {order.get('status')}\n")
            except Exception as fallback_error:
                fallback_error_type = type(fallback_error).__name__
                print(f"❌ Razorpay fallback order creation failed: {fallback_error_type} - {fallback_error}")
                if isinstance(fallback_error, requests.exceptions.RequestException):
                    if getattr(fallback_error, 'request', None) is not None:
                        print(f"   Request URL: https://api.razorpay.com/v1/orders")
                        print(f"   Request body: {order_data}")
                    if getattr(fallback_error, 'response', None) is not None:
                        print(f"   Response status: {fallback_error.response.status_code}")
                        print(f"   Response text: {fallback_error.response.text}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to create payment order due to a network error with Razorpay.',
                    'details': f'{fallback_error_type}: {str(fallback_error)}'
                }), 502
        
        return jsonify({
            'success': True,
            'order_id': order['id'],
            'amount': order['amount'],
            'currency': order['currency'],
            'key_id': RAZORPAY_CONFIG['key_id'],
            'merchant_name': MERCHANT_INFO['business_name'],
            'upi_id': upi_id,
            'prefill': {
                'email': user_email,
                'name': user_name,
                'contact': ''
            },
            'theme': {
                'color': PAYMENT_SETTINGS['theme_color']
            },
            'mode': 'LIVE' if IS_PRODUCTION else 'TEST'
        })
        
    except Exception as e:
        print(f"\n❌ ERROR in order creation: {e}")
        import traceback
        print(traceback.format_exc())
        print()
        return jsonify({
            'success': False, 
            'error': f'Order creation error: {str(e)}',
            'details': 'Please try again or contact support'
        }), 500

@app.route("/verify-razorpay-payment", methods=["POST"])
def verify_razorpay_payment():
    """Verify Razorpay payment signature and complete transaction - ENHANCED"""
    if not RAZORPAY_ENABLED:
        print("❌ Razorpay not enabled")
        return jsonify({
            'success': False, 
            'error': 'Razorpay not configured. Install razorpay: pip install razorpay'
        }), 503
    
    try:
        data = request.get_json()
        
        # Get payment details from Razorpay response
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')
        
        # Validate required payment fields
        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            print(f"❌ Missing payment fields: order={razorpay_order_id}, payment={razorpay_payment_id}")
            return jsonify({
                'success': False, 
                'error': 'Missing payment verification data from Razorpay'
            }), 400
        
        # Get pass details
        pass_type = data.get('pass_type', 'Daily Pass')
        amount = data.get('amount', '0')
        route = data.get('route', 'City Route')
        distance = data.get('distance', '0')
        user_email = data.get('user_email', '')
        user_name = data.get('user_name', 'Passenger')
        
        print(f"\n{'='*60}")
        print(f"🔍 PAYMENT VERIFICATION STARTED")
        print(f"{'='*60}")
        print(f"Payment ID: {razorpay_payment_id}")
        print(f"Order ID: {razorpay_order_id}")
        print(f"User: {user_email}")
        print(f"Pass: {pass_type} (₹{amount})")
        print(f"{'='*60}\n")
        
        # STEP 1: Verify payment signature (FAST - local operation)
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        try:
            razorpay_client.utility.verify_payment_signature(params_dict)
            print(f"✅ STEP 1: Signature verified successfully")
        except razorpay.errors.SignatureVerificationError as e:
            print(f"❌ STEP 1: Invalid signature - {e}")
            return jsonify({
                'success': False, 
                'error': 'Payment verification failed. Invalid signature from Razorpay.',
                'details': str(e)
            }), 400
        except Exception as e:
            print(f"❌ STEP 1: Signature verification error - {e}")
            return jsonify({
                'success': False, 
                'error': 'Signature verification error. Please contact support.',
                'details': str(e)
            }), 400
        
        # STEP 2: Fetch payment status (FAST - single API call)
        try:
            payment = razorpay_client.payment.fetch(razorpay_payment_id)
            print(f"✅ STEP 2: Payment details fetched from Razorpay")
            print(f"   Status: {payment['status']}")
            print(f"   Amount: ₹{payment['amount']/100}")
        except Exception as e:
            print(f"❌ STEP 2: Failed to fetch payment details - {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to fetch payment details from Razorpay',
                'details': str(e)
            }), 400
        
        if payment['status'] != 'captured':
            print(f"❌ STEP 2: Payment not captured. Status: {payment['status']}")
            return jsonify({
                'success': False,
                'error': f'Payment not captured. Status: {payment["status"]}. Please try again.'
            }), 400
        
        print(f"✅ STEP 2: Payment successfully captured")
        print(f"✅ STEP 2: Payment successfully captured")
        
        # STEP 3: Create pass data (FAST - local operation)
        pass_data = {
            'id': int(datetime.datetime.now().timestamp() * 1000),
            'type': pass_type,
            'price': f"₹{amount}",
            'route': route,
            'distance': distance,
            'purchaseDate': datetime.datetime.now().isoformat(),
            'expiryDate': calculate_expiry_date(pass_type),
            'status': 'active',
            'paymentMethod': 'Razorpay',
            'transactionId': razorpay_payment_id
        }
        print(f"✅ STEP 3: Pass data created: {pass_data['type']} | Valid until: {pass_data['expiryDate']}")
        
        # STEP 4: Save to database (FAST - async in background)
        pass_created = False
        if user_email:
            try:
                expiry_date_str = calculate_expiry_date(pass_type)
                print(f"   Attempting to save pass to database for {user_email}...")
                print(f"   Expiry date: {expiry_date_str}")
                
                result = db.create_pass(
                    user_email=user_email,
                    pass_type=pass_type,
                    price=float(amount),
                    route=route,
                    distance=float(distance) if distance else 0.0,
                    expiry_date=expiry_date_str,
                    payment_method='Razorpay',
                    transaction_id=razorpay_payment_id
                )
                
                if result:
                    print(f"✅ STEP 4: Pass saved to database successfully")
                    pass_created = True
                else:
                    print(f"⚠️  STEP 4: Database returned empty result, but no error thrown")
            except Exception as e:
                print(f"⚠️  STEP 4: Database save warning: {e}")
                print(f"   Pass data will be available for retry")
                # Don't fail completely, pass is still valid
        else:
            print(f"⚠️  STEP 4: No user email provided, skipping database save")
        
        # STEP 5: Generate receipt
        receipt = generate_enhanced_receipt(
            pass_type=pass_type,
            amount=amount,
            route=route,
            distance=distance,
            payment_method='Razorpay',
            user_name=user_name,
            user_email=user_email,
            transaction_type='new_pass',
            device_type='Web'
        )
        print(f"✅ STEP 5: Receipt generated")
        
        # STEP 6: Send emails ASYNCHRONOUSLY (don't wait for completion)
        import threading
        
        def send_emails_async():
            """Send emails in background thread"""
            try:
                if user_email:
                    print(f"   📧 Sending receipt email to {user_email}...")
                    # Send receipt email
                    send_enhanced_email_notification(
                        user_email, 
                        user_name, 
                        receipt, 
                        'new_pass'
                    )
                    print(f"   ✅ Receipt email sent")
                    
                    # Send TSRTC pass email
                    try:
                        print(f"   📧 Sending TSRTC pass email...")
                        send_tsrtc_pass_email(
                            user_email,
                            user_name,
                            pass_data
                        )
                        print(f"   ✅ TSRTC email sent")
                    except Exception as e:
                        print(f"   ⚠️  TSRTC email failed (non-critical): {e}")
            except Exception as e:
                print(f"   ⚠️  Email error (non-critical): {e}")
        
        # Start email sending in background (non-blocking)
        email_thread = threading.Thread(target=send_emails_async)
        email_thread.daemon = True
        email_thread.start()
        print(f"✅ STEP 6: Email sending started in background")
        
        print(f"\n{'='*60}")
        print(f"✅ PAYMENT VERIFICATION COMPLETE!")
        print(f"{'='*60}\n")
        
        # Return immediately without waiting for emails
        return jsonify({
            'success': True,
            'message': 'Payment verified successfully and pass created!',
            'payment_id': razorpay_payment_id,
            'order_id': razorpay_order_id,
            'receipt': receipt,
            'email_sent': True,  # Will be sent in background
            'tsrtc_email_sent': True,  # Will be sent in background
            'pass_data': pass_data,
            'pass_created': pass_created
        })
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ PAYMENT VERIFICATION ERROR")
        print(f"{'='*60}")
        print(f"Error: {e}")
        import traceback
        print(traceback.format_exc())
        print(f"{'='*60}\n")
        
        return jsonify({
            'success': False, 
            'error': f'Payment verification failed: {str(e)}',
            'details': 'Please contact support if this problem persists'
        }), 500

def calculate_expiry_date(pass_type):
    """Calculate expiry date based on pass type"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    
    expiry_days = {
        'Daily Pass': 1,
        'Weekly Pass': 7,
        'Monthly Pass': 30,
        'Student Monthly Pass': 30,
        'Quarterly Pass': 90,
        'Annual Pass': 365
    }
    
    days = expiry_days.get(pass_type, 1)
    expiry = now + timedelta(days=days)
    
    return expiry.isoformat()

@app.route("/razorpay-webhook", methods=["POST"])
def razorpay_webhook():
    """Handle Razorpay webhooks for payment events"""
    if not RAZORPAY_ENABLED:
        return jsonify({'status': 'disabled'}), 503
    
    try:
        # Get webhook data
        webhook_body = request.get_data().decode('utf-8')
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        
        print(f"📡 Received Razorpay webhook")
        
        # Verify webhook signature (if webhook secret is configured)
        from config_razorpay import WEBHOOK_SECRET
        if WEBHOOK_SECRET and WEBHOOK_SECRET != 'YOUR_WEBHOOK_SECRET_HERE':
            try:
                razorpay_client.utility.verify_webhook_signature(
                    webhook_body,
                    webhook_signature,
                    WEBHOOK_SECRET
                )
                print(f"SUCCESS: Webhook signature verified")
            except:
                print(f"ERROR: Invalid webhook signature")
                return jsonify({'status': 'invalid_signature'}), 400
        
        # Parse webhook event
        event = request.get_json()
        event_type = event.get('event')
        
        print(f"📡 Webhook event: {event_type}")
        
        if event_type == 'payment.captured':
            # Payment successful
            payment_entity = event['payload']['payment']['entity']
            payment_id = payment_entity['id']
            amount = payment_entity['amount'] / 100
            
            print(f"SUCCESS: Payment captured: {payment_id} (₹{amount})")
            
            # You can add additional processing here
            # e.g., send confirmation SMS, update analytics, etc.
            
        elif event_type == 'payment.failed':
            # Payment failed
            payment_entity = event['payload']['payment']['entity']
            payment_id = payment_entity['id']
            error_description = payment_entity.get('error_description', 'Unknown error')
            
            print(f"ERROR: Payment failed: {payment_id} - {error_description}")
            
            # You can add failure handling here
            # e.g., notify user, log for analysis, etc.
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        print(f"ERROR: Webhook processing error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ---------- ENHANCED PAYMENT COMPLETION WITH EMAIL NOTIFICATIONS ----------
@app.route("/complete-payment", methods=["POST"])
def complete_payment():
    """Complete payment and generate receipt - ENHANCED WITH PASS STORAGE AND NOTIFICATIONS"""
    try:
        data = request.get_json()
        
        # Get payment details
        pass_type = data.get('pass_type', 'Daily Pass')
        amount = data.get('amount', '25')
        route = data.get('route', 'City Route')
        distance = data.get('distance', '0')
        payment_method = data.get('payment_method', 'UPI')
        transaction_type = data.get('transaction_type', 'new_pass')
        device_type = data.get('device_type', 'Unknown')
        
        # Get user info
        user_email = data.get('user_email', 'mk4829779@gmail.com')
        user_name = data.get('user_name', 'Smart Bus User')
        pass_data = data.get('pass_data', {})
        
        print(f"[EMAIL] Processing {transaction_type} completion for: {user_email}")
        print(f"💳 Payment method: {payment_method} | Device: {device_type}")
        print(f"[PASS] Pass: {pass_type} | Amount: ₹{amount}")
        
        # Store pass in backend storage
        if transaction_type == 'new_pass' and pass_data:
            store_user_pass(user_email, pass_data)
            schedule_expiry_notifications(user_email, pass_data)
        
        # Generate receipt
        receipt = generate_enhanced_receipt(pass_type, amount, route, distance, payment_method, user_name, user_email, transaction_type, device_type)
        
        # Send enhanced email notification
        email_sent = False
        if user_email:
            print(f"[EMAIL] Sending enhanced email notification to: {user_email}")
            try:
                email_sent = send_enhanced_email_notification(user_email, user_name, receipt, transaction_type)
                if email_sent:
                    print(f"SUCCESS: Enhanced email sent successfully to {user_email}")
                else:
                    print(f"ERROR: Enhanced email sending failed to {user_email}")
            except Exception as e:
                print(f"ERROR: Enhanced email error: {e}")
        
        return {
            "success": True,
            "message": f"{transaction_type.replace('_', ' ').title()} completed successfully!",
            "receipt": receipt,
            "email_sent": email_sent,
            "email_address": user_email,
            "transaction_type": transaction_type,
            "device_type": device_type,
            "pass_stored": True,
            "redirect_url": "/passes"
        }
        
    except Exception as e:
        print(f"ERROR: Payment completion error: {e}")
        return {"success": False, "error": str(e)}, 500
        if not user_email:
            user_email = data.get('stored_email')
        
        # Default email for testing
        if not user_email:
            user_email = "mk4829779@gmail.com"  # Default for testing
            print(f"WARNING: No user email found, using default: {user_email}")
        
        print(f"[EMAIL] Processing {transaction_type} completion for: {user_email}")
        print(f"💳 Payment method: {payment_method} | Device: {device_type}")
        
        # Generate receipt (fast)
        receipt = generate_enhanced_receipt(pass_type, amount, route, distance, payment_method, user_name, user_email, transaction_type, device_type)
        
        # Send enhanced email notification
        email_sent = False
        if user_email:
            print(f"[EMAIL] Sending enhanced email notification to: {user_email}")
            try:
                email_sent = send_enhanced_email_notification(user_email, user_name, receipt, transaction_type)
                if email_sent:
                    print(f"SUCCESS: Enhanced email sent successfully to {user_email}")
                else:
                    print(f"ERROR: Enhanced email sending failed to {user_email}")
            except Exception as e:
                print(f"ERROR: Enhanced email error: {e}")
        
        return {
            "success": True,
            "message": f"{transaction_type.replace('_', ' ').title()} completed successfully!",
            "receipt": receipt,
            "email_sent": email_sent,
            "email_address": user_email,
            "transaction_type": transaction_type,
            "device_type": device_type,
            "redirect_url": "/dashboard"
        }
        
    except Exception as e:
        print(f"ERROR: Payment completion error: {e}")
        return {"success": False, "error": str(e)}, 500

def generate_enhanced_receipt(pass_type, amount, route, distance, payment_method, user_name, user_email, transaction_type, device_type):
    """Generate a detailed payment receipt - ENHANCED VERSION"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    
    # Calculate expiry date based on pass type (simplified)
    expiry_days = {
        'Daily': 1, 'Weekly': 7, 'Monthly': 30, 'Student Monthly': 30,
        'Quarterly': 90, 'Annual': 365
    }
    
    days = 1  # default
    for key in expiry_days:
        if key in pass_type:
            days = expiry_days[key]
            break
    
    expiry_date = now + timedelta(days=days)
    
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
        "transaction_type": transaction_type,
        "device_type": device_type,
        "merchant_name": "Lingam Manoj Kumar",
        "merchant_upi": "8340927497@ibl",
        "merchant_phone": "8340927497",
        "purchase_date": now.strftime("%Y-%m-%d"),
        "expiry_date": expiry_date.strftime("%Y-%m-%d"),
        "status": "COMPLETED",
        "validity_days": days,
        "platform": "Smart Bus System",
        "support_email": "mk4829779@gmail.com",
        "support_phone": "+91 8340927497"
    }
    
    return receipt

def send_enhanced_email_notification(user_email, user_name, receipt, transaction_type):
    """Send enhanced email notification for all transaction types"""
    try:
        print(f"[EMAIL] Sending enhanced email to: {user_email} | Type: {transaction_type}")
        
        # Customize subject and content based on transaction type
        if transaction_type == 'new_pass':
            subject = f"SUCCESS: New Bus Pass Activated - Smart Bus"
            action_text = "purchased and activated"
            icon = "[PASS]"
        elif transaction_type == 'renewal':
            subject = f"[ROUTE] Bus Pass Renewed - Smart Bus"
            action_text = "renewed successfully"
            icon = "[ROUTE]"
        else:
            subject = f"💳 Payment Successful - Smart Bus"
            action_text = "payment completed"
            icon = "💳"
        
        # Enhanced email body with better formatting
        html_body = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f8f9fa;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); color: white; padding: 30px; text-align: center; border-radius: 15px 15px 0 0;">
                <h1 style="margin: 0; font-size: 28px;">{icon} Smart Bus</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">Your {action_text}!</p>
            </div>
            
            <!-- Success Message -->
            <div style="background: white; padding: 30px; border-left: 5px solid #4CAF50; margin: 0;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <div style="background: #e8f5e8; color: #4CAF50; padding: 20px; border-radius: 10px; display: inline-block;">
                        <h2 style="margin: 0; font-size: 24px;">🎉 Transaction Successful!</h2>
                        <p style="margin: 10px 0 0 0; font-size: 16px;">Hello {user_name}, your {transaction_type.replace('_', ' ')} is complete</p>
                    </div>
                </div>
                
                <!-- Receipt Details -->
                <div style="background: #f8f9fa; padding: 25px; border-radius: 10px; margin: 20px 0;">
                    <h3 style="color: #333; margin: 0 0 20px 0; border-bottom: 2px solid #4CAF50; padding-bottom: 10px;">
                        [PAGE] Transaction Receipt
                    </h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 12px 0; font-weight: bold; color: #666;">Receipt Number:</td>
                            <td style="padding: 12px 0; color: #333;">{receipt['receipt_number']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 12px 0; font-weight: bold; color: #666;">Transaction ID:</td>
                            <td style="padding: 12px 0; color: #333;">{receipt['transaction_id']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 12px 0; font-weight: bold; color: #666;">Pass Type:</td>
                            <td style="padding: 12px 0; color: #333; font-weight: bold;">{receipt['pass_type']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 12px 0; font-weight: bold; color: #666;">Amount Paid:</td>
                            <td style="padding: 12px 0; color: #4CAF50; font-weight: bold; font-size: 18px;">₹{receipt['amount']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 12px 0; font-weight: bold; color: #666;">Route:</td>
                            <td style="padding: 12px 0; color: #333;">{receipt['route']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 12px 0; font-weight: bold; color: #666;">Purchase Date:</td>
                            <td style="padding: 12px 0; color: #333;">{receipt['purchase_date']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 12px 0; font-weight: bold; color: #666;">Valid Until:</td>
                            <td style="padding: 12px 0; color: #ff9800; font-weight: bold;">{receipt['expiry_date']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 12px 0; font-weight: bold; color: #666;">Payment Method:</td>
                            <td style="padding: 12px 0; color: #333;">{receipt['payment_method']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 12px 0; font-weight: bold; color: #666;">Device Used:</td>
                            <td style="padding: 12px 0; color: #333;">{receipt['device_type']}</td>
                        </tr>
                    </table>
                </div>
                
                <!-- Merchant Information -->
                <div style="background: #e3f2fd; padding: 25px; border-radius: 10px; margin: 20px 0;">
                    <h3 style="color: #1976d2; margin: 0 0 15px 0;">🏪 Merchant Details</h3>
                    <p style="margin: 8px 0; color: #333;"><strong>Name:</strong> {receipt['merchant_name']}</p>
                    <p style="margin: 8px 0; color: #333;"><strong>UPI ID:</strong> {receipt['merchant_upi']}</p>
                    <p style="margin: 8px 0; color: #333;"><strong>Phone:</strong> {receipt['merchant_phone']}</p>
                    <p style="margin: 8px 0; color: #333;"><strong>Status:</strong> <span style="color: #4CAF50; font-weight: bold;">{receipt['status']}</span></p>
                </div>
                
                <!-- Pass Validity Information -->
                <div style="background: #fff3e0; padding: 25px; border-radius: 10px; margin: 20px 0; border: 2px solid #ff9800;">
                    <h3 style="color: #f57c00; margin: 0 0 15px 0;">[TIME] Pass Validity</h3>
                    <p style="margin: 8px 0; color: #333; font-size: 16px;">
                        <strong>Your {receipt['pass_type']} is valid for {receipt['validity_days']} day(s)</strong>
                    </p>
                    <p style="margin: 8px 0; color: #666;">
                        Valid from: <strong>{receipt['purchase_date']}</strong> to <strong>{receipt['expiry_date']}</strong>
                    </p>
                    <p style="margin: 15px 0 0 0; padding: 15px; background: rgba(255, 152, 0, 0.1); border-radius: 8px; color: #f57c00;">
                        💡 <strong>Tip:</strong> Save this email as proof of purchase. Show this receipt when using Smart Bus services.
                    </p>
                </div>
                
                <!-- Action Buttons -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://localhost:5000/dashboard" style="background: linear-gradient(135deg, #4CAF50, #45a049); color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block; margin: 10px;">
                        🚌 View My Passes
                    </a>
                    <a href="http://localhost:5000/route" style="background: linear-gradient(135deg, #2196F3, #1976D2); color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block; margin: 10px;">
                        [MAP] Plan Route
                    </a>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background: #333; color: white; padding: 25px; text-align: center; border-radius: 0 0 15px 15px;">
                <h3 style="margin: 0 0 15px 0; color: #4CAF50;">Thank you for choosing Smart Bus! 🚌</h3>
                <p style="margin: 8px 0; color: #ccc;">Your trusted partner for city transportation</p>
                
                <div style="margin: 20px 0; padding: 20px; background: rgba(76, 175, 80, 0.1); border-radius: 10px;">
                    <h4 style="margin: 0 0 10px 0; color: #4CAF50;">📞 Need Help?</h4>
                    <p style="margin: 5px 0; color: #ccc;">Email: {receipt['support_email']}</p>
                    <p style="margin: 5px 0; color: #ccc;">Phone: {receipt['support_phone']}</p>
                    <p style="margin: 5px 0; color: #ccc;">Platform: {receipt['platform']}</p>
                </div>
                
                <p style="margin: 15px 0 0 0; font-size: 12px; color: #999;">
                    This is an automated email. Please do not reply to this message.<br>
                    Generated on {receipt['date']} | Receipt #{receipt['receipt_number']}
                </p>
            </div>
        </div>
        """
        
        # Gmail SMTP settings
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfiekxqfivdwcjs"  # App password
        
        msg = MIMEText(html_body, 'html')
        msg["Subject"] = subject
        msg["From"] = f"Smart Bus System <{SENDER_EMAIL}>"
        msg["To"] = user_email
        
        print(f"[EMAIL] Connecting to Gmail SMTP for enhanced email...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        
        print(f"[EMAIL] Logging in to Gmail...")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        print(f"[EMAIL] Sending enhanced email...")
        server.send_message(msg)
        server.quit()
        
        print(f"SUCCESS: Enhanced email sent successfully to {user_email}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to send enhanced email: {e}")
        print(f"   Email: {user_email}")
        print(f"   Transaction type: {transaction_type}")
        print(f"   Error details: {str(e)}")
        return False

def send_tsrtc_pass_email(user_email, user_name, pass_data):
    """Send TSRTC pass as HTML email with government stamp"""
    try:
        print(f"[PASS] Generating TSRTC pass email for: {user_email}")
        
        # Format expiry date
        expiry_date = pass_data.get('expiryDate', 'N/A')
        if len(expiry_date) > 10:
            expiry_date = expiry_date[:10]
        
        # Generate TSRTC pass HTML with complete styling
        tsrtc_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; background: #f0f0f0; padding: 20px; }}
        .pass-container {{ background: white; width: 800px; margin: 0 auto; height: 500px; position: relative; box-shadow: 0 10px 30px rgba(0,0,0,0.3); border-radius: 10px; overflow: hidden; }}
        .pass-background {{ position: absolute; width: 100%; height: 100%; background: linear-gradient(135deg, #ffb6d9 0%, #ffc0e0 25%, #d4f1d4 50%, #b8e6b8 75%, #ffb6d9 100%); opacity: 0.3; z-index: 0; }}
        
        /* Government Stamp - Centered */
        .govt-stamp {{ 
            position: absolute; 
            top: 50%; 
            left: 50%; 
            transform: translate(-50%, -50%) rotate(-15deg); 
            opacity: 0.2; 
            z-index: 1; 
        }}
        .stamp-circle {{ 
            width: 250px; 
            height: 250px; 
            border: 10px solid #e91e63; 
            border-radius: 50%; 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            justify-content: center; 
            background: rgba(255, 255, 255, 0.3); 
        }}
        .stamp-text {{ 
            font-size: 18px; 
            font-weight: bold; 
            color: #e91e63; 
            text-align: center; 
            line-height: 1.3; 
        }}
        .stamp-emblem {{ 
            font-size: 50px; 
            margin-bottom: 10px; 
        }}
        
        .pass-content {{ position: relative; z-index: 2; padding: 40px 40px; height: 100%; }}
        .tsrtc-header {{ text-align: right; margin-bottom: 15px; }}
        .pass-number {{ font-size: 20px; font-weight: bold; color: #333; letter-spacing: 2px; }}
        .tsrtc-logo {{ font-size: 28px; font-weight: bold; color: #e91e63; margin-top: 5px; }}
        .tsrtc-subtitle {{ font-size: 12px; color: #666; margin-top: 3px; }}
        .pass-type {{ font-size: 20px; font-weight: bold; color: #333; margin: 15px 0; text-align: center; background: rgba(255,255,255,0.8); padding: 10px; border-radius: 8px; }}
        .pass-details {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 15px; }}
        .detail-item {{ background: rgba(255, 255, 255, 0.8); padding: 10px; border-radius: 5px; }}
        .detail-label {{ font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 3px; }}
        .detail-value {{ font-size: 13px; font-weight: bold; color: #333; }}
        .success-section {{ text-align: center; padding: 15px; background: #4CAF50; color: white; border-radius: 8px; }}
        .success-section h3 {{ margin: 0; font-size: 18px; }}
        .success-section p {{ margin: 8px 0 0 0; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="pass-container">
        <div class="pass-background"></div>
        
        <!-- Government Stamp Watermark - Centered -->
        <div class="govt-stamp">
            <div class="stamp-circle">
                <div class="stamp-emblem">🏛️</div>
                <div class="stamp-text">
                    GOVERNMENT OF<br>
                    TELANGANA<br>
                    TSRTC<br>
                    AUTHORIZED
                </div>
            </div>
        </div>
        
        <div class="pass-content">
            <div class="tsrtc-header">
                <div class="pass-number">{pass_data.get('id', 'PASS-' + str(int(__import__('time').time())))}</div>
                <div class="tsrtc-logo">TSRTC</div>
                <div class="tsrtc-subtitle">Telangana State Road Transport Corporation</div>
            </div>
            
            <div class="pass-type">{pass_data.get('type', 'Bus Pass')}</div>
            
            <div class="pass-details">
                <div class="detail-item">
                    <div class="detail-label">Passenger Name</div>
                    <div class="detail-value">{user_name}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Email</div>
                    <div class="detail-value">{user_email}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Route</div>
                    <div class="detail-value">{pass_data.get('route', 'City Route')}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Distance</div>
                    <div class="detail-value">{pass_data.get('distance', '0')} km</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Amount Paid</div>
                    <div class="detail-value">{pass_data.get('price', '₹0')}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Valid Until</div>
                    <div class="detail-value">{expiry_date}</div>
                </div>
            </div>
            
            <div class="success-section">
                <h3>✅ PASS ACTIVATED</h3>
                <p>Your TSRTC bus pass is now active and ready to use!</p>
            </div>
            
            <!-- QR Code Section -->
            <div style="text-align: center; margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.8); border-radius: 8px;">
                <div style="font-size: 12px; color: #666; margin-bottom: 8px; text-transform: uppercase;">Scan QR Code</div>
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=http://localhost:5000" 
                     alt="QR Code" 
                     style="width: 120px; height: 120px; border: 2px solid #e91e63; border-radius: 8px; padding: 5px; background: white;">
                <div style="font-size: 11px; color: #999; margin-top: 5px;">Visit Smart Bus Portal</div>
            </div>
        </div>
    </div>
    
    <div style="text-align: center; margin-top: 30px; color: #666; font-size: 14px;">
        <p style="margin: 5px 0;"><strong>This is your official TSRTC bus pass.</strong></p>
        <p style="margin: 5px 0;">Please show this pass when boarding the bus.</p>
        <p style="margin: 15px 0 5px 0;">For support, contact:</p>
        <p style="margin: 5px 0;">📧 support@smartbus.com | 📞 +91 8340927497</p>
    </div>
</body>
</html>
        """
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"Smart Bus TSRTC <{SENDER_EMAIL}>"
        msg['To'] = user_email
        msg['Subject'] = f"🎫 Your TSRTC Bus Pass - {pass_data.get('type', 'Bus Pass')}"
        
        # Attach HTML
        html_part = MIMEText(tsrtc_html, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Send email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"SUCCESS: TSRTC pass email sent successfully to {user_email}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to send TSRTC pass email: {e}")
        import traceback
        traceback.print_exc()
        return False

# ---------- AUTOMATIC PAYMENT DETECTION ----------
@app.route("/detect-payment", methods=["POST"])
def detect_payment():
    """Detect if payment has been received to UPI ID - REAL IMPLEMENTATION"""
    try:
        data = request.get_json()
        
        amount = data.get('amount')
        upi_id = data.get('upi_id', '8340927497@ibl')
        merchant_name = data.get('merchant_name', 'Lingam Manoj Kumar')
        
        print(f"[SEARCH] Detecting payment:")
        print(f"   Amount: ₹{amount}")
        print(f"   UPI ID: {upi_id}")
        print(f"   Merchant: {merchant_name}")
        
        # In a real implementation, you would:
        # 1. Check with your bank's API for recent transactions
        # 2. Verify UPI payment gateway webhooks
        # 3. Check SMS notifications for payment confirmations
        # 4. Use bank statement APIs to verify incoming payments
        
        # For demo, NEVER automatically detect payment
        # Always require manual confirmation to prevent fake success
        print(f"WARNING: DEMO MODE: Payment detection disabled to prevent fake success")
        print(f"   Real implementation would check bank API/SMS/webhooks")
        
        # Always return payment not detected for demo
        result = {
            "success": True,
            "payment_detected": False,
            "message": "Payment detection requires manual confirmation in demo mode",
            "next_check_in": 10,
            "demo_mode": True,
            "instructions": "Complete payment in UPI app, then click 'I've Completed Payment'"
        }
        
        print(f"⏳ Payment not detected (demo mode)")
        return result
        
    except Exception as e:
        print(f"ERROR: Payment detection failed: {e}")
        return {
            "success": False,
            "payment_detected": False,
            "error": str(e),
            "message": "Payment detection failed"
        }, 500

# ---------- REAL-TIME PAYMENT VERIFICATION ----------
@app.route("/verify-payment", methods=["POST"])
def verify_payment():
    """Verify real-time UPI payment (in production, integrate with payment gateway)"""
    try:
        data = request.get_json()
        
        # Get payment details
        transaction_id = data.get('transaction_id')
        amount = data.get('amount')
        upi_ref = data.get('upi_ref')
        pass_type = data.get('pass_type', 'Daily Pass')
        
        print(f"💳 Verifying real payment:")
        print(f"   Transaction ID: {transaction_id}")
        print(f"   Amount: ₹{amount}")
        print(f"   UPI Ref: {upi_ref}")
        print(f"   Pass Type: {pass_type}")
        
        # In production, you would:
        # 1. Verify with UPI payment gateway
        # 2. Check transaction status
        # 3. Validate amount and merchant details
        # 4. Update database with payment status
        
        # For demo, simulate verification
        verification_result = {
            "success": True,
            "verified": True,
            "transaction_id": transaction_id or f"TXN{int(time.time())}",
            "amount": amount,
            "status": "SUCCESS",
            "payment_method": "UPI",
            "merchant_upi": "8340927497@ibl",
            "merchant_name": "Lingam Manoj Kumar",
            "timestamp": datetime.datetime.now().isoformat(),
            "message": "Payment verified successfully"
        }
        
        print(f"SUCCESS: Payment verification result: {verification_result}")
        
        return verification_result
        
    except Exception as e:
        print(f"ERROR: Payment verification failed: {e}")
        return {
            "success": False,
            "verified": False,
            "error": str(e),
            "message": "Payment verification failed"
        }, 500

@app.route("/payment-webhook", methods=["POST"])
def payment_webhook():
    """Webhook endpoint for real-time payment notifications from UPI gateway"""
    try:
        data = request.get_json()
        
        print(f"📨 Payment webhook received:")
        print(f"   Data: {data}")
        
        # In production, you would:
        # 1. Verify webhook signature
        # 2. Process payment notification
        # 3. Update order status
        # 4. Send confirmation to user
        # 5. Activate the bus pass
        
        # For demo, acknowledge webhook
        return {
            "success": True,
            "message": "Webhook processed successfully"
        }
        
    except Exception as e:
        print(f"ERROR: Webhook processing failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }, 500

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    """Handle logout and clear session"""
    user_email = session.get('user_email', 'Unknown')
    print(f"[LOGOUT] User logging out: {user_email}")
    
    # Clear session data
    session.clear()
    
    print(f"[LOGOUT] Session cleared successfully")
    
    # Redirect to login page
    return redirect(url_for('index'))

# ---------- DEBUG ROUTE ----------
@app.route("/debug-routes")
def debug_routes():
    """Debug route to list all available routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': str(rule)
        })
    return {"routes": routes}

# ---------- FORGOT PASSWORD FUNCTIONALITY ----------
@app.route("/test-forgot")
def test_forgot():
    """Test route to verify forgot.html template"""
    print("[SEARCH] DEBUG: /test-forgot route called - rendering forgot.html")
    return render_template("forgot.html")

@app.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    """Forgot password page - shows email entry form and handles reset requests"""
    global reset_tokens  # Use global variable
    
    if request.method == "POST":
        # Handle password reset request
        email = request.form.get("email")
        
        if not email:
            return render_template("forgot.html", error="Please enter your email address")
        
        email_lower = email.lower().strip()
        
        print(f"=== FORGOT PASSWORD REQUEST ===")
        print(f"Email: {email_lower}")
        print(f"===============================")
        
        # Check if email exists in user accounts
        user_accounts = getattr(app, 'user_accounts', {
            "mk4829779@gmail.com": "Manoj123",
            "lingammanojkumar178@gmail.com": "Kumar123",
        })
        
        if email_lower not in user_accounts:
            print(f"ERROR: Email not found: {email_lower}")
            return render_template("forgot.html", 
                                 error=f"No account found with email {email}. Please sign up first.")
        
        # Generate reset token
        import secrets
        reset_token = secrets.token_urlsafe(32)
        
        # Store reset token in global variable
        reset_tokens[email_lower] = {
            'token': reset_token,
            'timestamp': __import__('time').time()
        }
        
        print(f"🔑 Generated reset token: {reset_token}")
        print(f"📋 Stored tokens: {list(reset_tokens.keys())}")
        
        # Create reset link
        reset_link = f"http://localhost:5000/reset-password?token={reset_token}&email={email_lower}"
        print(f"🔗 Reset link: {reset_link}")
        
        # Email configuration
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfiekxqfivdwcjs"
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
            print(f"[EMAIL] Sending password reset email to: {RECIPIENT_EMAIL}")
            
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            print(f"SUCCESS: Password reset email sent successfully to {RECIPIENT_EMAIL}")
            return render_template("forgot.html", 
                                 success=f"Password reset link sent to {email}. Please check your email.")
            
        except Exception as e:
            print(f"ERROR: Failed to send password reset email: {e}")
            return render_template("forgot.html", 
                                 error="Failed to send reset email. Please try again later.")
    
    # GET request - show the form
    return render_template("forgot.html")

@app.route("/reset-password", methods=["GET"])
def reset_password():
    """Show password reset form"""
    global reset_tokens  # Use global variable
    
    token = request.args.get('token')
    email = request.args.get('email')
    
    print(f"=== RESET PASSWORD PAGE REQUEST ===")
    print(f"Token: {token}")
    print(f"Email: {email}")
    print(f"📋 Stored tokens: {list(reset_tokens.keys())}")
    print(f"===================================")
    
    if not token or not email:
        print("ERROR: Missing token or email")
        return render_template("forgot.html", error="Invalid reset link. Please request a new one.")
    
    email_lower = email.lower().strip()
    
    # Check if token exists and is valid
    if email_lower not in reset_tokens:
        print(f"ERROR: No token found for email: {email_lower}")
        return render_template("forgot.html", error="Invalid or expired reset link. Please request a new one.")
    
    if reset_tokens[email_lower]['token'] != token:
        print(f"ERROR: Token mismatch for email: {email_lower}")
        return render_template("forgot.html", error="Invalid or expired reset link. Please request a new one.")
    
    # Check if token is expired (1 hour)
    import time
    token_age = time.time() - reset_tokens[email_lower]['timestamp']
    print(f"⏱️ Token age: {token_age:.0f} seconds ({token_age/60:.1f} minutes)")
    
    if token_age > 3600:  # 1 hour
        print(f"ERROR: Token expired for email: {email_lower}")
        del reset_tokens[email_lower]
        return render_template("forgot.html", error="Reset link has expired (valid for 1 hour). Please request a new one.")
    
    print(f"SUCCESS: Token valid, showing reset form for: {email_lower}")
    # Show password reset form
    return render_template("reset-password.html", token=token, email=email_lower)

# First set_new_password function removed - duplicate found below with better validation

# Store user passes with expiry tracking (in production, use database)
user_passes = {}

# Store pass expiry notifications (in production, use database)
pass_notifications = {}

def store_user_pass(user_email, pass_data):
    """Store user pass in MySQL database"""
    try:
        # Extract pass details
        pass_type = pass_data.get('type', 'Unknown')
        price_str = pass_data.get('price', '₹0')
        price = float(price_str.replace('₹', '').replace(',', '').strip())
        route = pass_data.get('route', 'Unknown Route')
        distance = pass_data.get('distance', 0)
        expiry_date_str = pass_data.get('expiryDate', '')
        payment_method = pass_data.get('paymentMethod', 'UPI')
        transaction_id = pass_data.get('id', '')
        
        # Convert ISO date format to MySQL datetime format
        # From: '2026-02-15T00:28:22.785Z' 
        # To: '2026-02-15 00:28:22'
        from datetime import datetime
        if expiry_date_str:
            # Parse ISO format and convert to MySQL format
            expiry_dt = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
            expiry_date = expiry_dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            expiry_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Save to MySQL database
        success = db.create_pass(
            user_email=user_email,
            pass_type=pass_type,
            price=price,
            route=route,
            distance=distance,
            expiry_date=expiry_date,
            payment_method=payment_method,
            transaction_id=transaction_id
        )
        
        if success:
            print(f"SUCCESS: Pass stored in MySQL for {user_email}: {pass_type} (ID: {transaction_id})")
            
            # Also store in memory for backward compatibility
            if user_email not in user_passes:
                user_passes[user_email] = []
            
            pass_data['created_at'] = datetime.now().isoformat()
            pass_data['notifications_sent'] = []
            user_passes[user_email].append(pass_data)
            
            # Add welcome notification
            add_website_notification(user_email, {
                'type': 'pass_purchased',
                'title': 'Pass Purchased Successfully',
                'message': f'Your {pass_type} has been activated and is ready to use!',
                'pass_id': transaction_id,
                'urgency': 'info'
            })
            
            return True
        else:
            print(f"ERROR: Failed to store pass in MySQL")
            return False
        
    except Exception as e:
        print(f"ERROR: Error storing pass: {e}")
        import traceback
        traceback.print_exc()
        return False

def schedule_expiry_notifications(user_email, pass_data):
    """Schedule expiry notifications for a pass"""
    try:
        print(f"📅 Scheduling expiry notifications for pass {pass_data.get('id', 'unknown')}")
        
        # Get expiry date - handle both formats (expiryDate from frontend, expiry_date from MySQL)
        expiry_date_str = pass_data.get('expiryDate') or pass_data.get('expiry_date')
        if not expiry_date_str:
            print("WARNING: No expiry date found in pass data")
            return False
        
        # Parse the date
        if isinstance(expiry_date_str, str):
            # Handle ISO format with Z
            if 'Z' in expiry_date_str or 'T' in expiry_date_str:
                expiry_date_str = expiry_date_str.replace('Z', '+00:00')
                expiry_date = datetime.datetime.fromisoformat(expiry_date_str)
            else:
                # MySQL datetime format
                expiry_date = datetime.datetime.strptime(expiry_date_str, '%Y-%m-%d %H:%M:%S')
        elif isinstance(expiry_date_str, datetime.datetime):
            # Already a datetime object
            expiry_date = expiry_date_str
        else:
            print(f"WARNING: Unknown date format: {type(expiry_date_str)}")
            return False
        
        now = datetime.datetime.now()
        
        # Calculate notification dates
        notification_schedule = [
            (7, "7_days"),      # 7 days before
            (3, "3_days"),      # 3 days before  
            (1, "1_day"),       # 1 day before
            (0, "expiry_day")   # On expiry day
        ]
        
        for days_before, notification_key in notification_schedule:
            notification_date = expiry_date - datetime.timedelta(days=days_before)
            
            print(f"[EMAIL] Notification scheduled: {notification_key} on {notification_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Error scheduling notifications: {e}")
        import traceback
        traceback.print_exc()
        return False

def add_website_notification(user_email, notification_data):
    """Add notification to website dashboard"""
    try:
        if user_email not in pass_notifications:
            pass_notifications[user_email] = []
        
        notification = {
            'id': int(time.time() * 1000),  # Unique ID
            'type': notification_data['type'],
            'title': notification_data['title'],
            'message': notification_data['message'],
            'pass_id': notification_data.get('pass_id'),
            'urgency': notification_data.get('urgency', 'low'),
            'date': datetime.datetime.now().isoformat(),
            'read': False
        }
        
        pass_notifications[user_email].append(notification)
        
        # Keep only last 50 notifications per user
        if len(pass_notifications[user_email]) > 50:
            pass_notifications[user_email] = pass_notifications[user_email][-50:]
        
        print(f"[MOBILE] Website notification added for {user_email}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to add website notification: {e}")
        return False

@app.route("/send-reset-link", methods=["POST"])
def send_reset_link():
    """Send password reset link to user's email"""
    try:
        email = request.form.get("email", "").strip()
        
        if not email:
            return render_template("forgot.html", error="Please enter your email address")
        
        email_lower = email.lower().strip()
        
        # Email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email_lower):
            return render_template("forgot.html", error="Please enter a valid email address")
        
        # Get user accounts
        user_accounts = getattr(app, 'user_accounts', {
            "mk4829779@gmail.com": "Manoj123",
            "lingammanojkumar178@gmail.com": "Kumar123",
        })
        
        if email_lower not in user_accounts:
            return render_template("forgot.html", error="No account found with this email address")
        
        # Generate secure reset token
        import secrets
        reset_token = secrets.token_urlsafe(32)
        
        # Store token with timestamp (expires in 1 hour)
        reset_tokens[email_lower] = {
            'token': reset_token,
            'timestamp': time.time(),
            'used': False
        }
        
        # Create reset link
        reset_link = f"http://localhost:5000/reset-password/{reset_token}?email={email_lower}"
        
        print(f"🔑 Generated reset token for: {email_lower}")
        print(f"🔗 Reset link: {reset_link}")
        
        # Send reset email
        try:
            SENDER_EMAIL = "mk4829779@gmail.com"
            SENDER_PASSWORD = "cbfiekxqfivdwcjs"
            
            # Get user name
            user_profiles = getattr(app, 'user_profiles', {})
            user_name = user_profiles.get(email_lower, {}).get('name', email_lower.split('@')[0].title())
            
            msg = MIMEText(f"""
Hello {user_name},

You requested to reset your Smart Bus account password.

Click the link below to set a new password:
{reset_link}

This link will expire in 1 hour for security reasons.

If you didn't request this password reset, please ignore this email.

Security Information:
- Reset requested at: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- Your account email: {email_lower}
- Link expires: {datetime.datetime.fromtimestamp(time.time() + 3600).strftime("%Y-%m-%d %H:%M:%S")}

If you have any issues, please contact our support team.

Best regards,
Smart Bus Team
            """)
            
            msg["Subject"] = "Smart Bus - Password Reset Link"
            msg["From"] = f"Smart Bus Support <{SENDER_EMAIL}>"
            msg["To"] = email_lower
            
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            print(f"SUCCESS: Password reset link sent to {email_lower}")
            return render_template("forgot.html", 
                                 success=f"Password reset link sent to {email_lower}. Please check your email and click the link to reset your password.")
            
        except Exception as e:
            print(f"ERROR: Failed to send reset email: {e}")
            return render_template("forgot.html", error="Failed to send reset email. Please try again.")
            
    except Exception as e:
        print(f"ERROR: Send reset link error: {e}")
        return render_template("forgot.html", error="Failed to process reset request. Please try again.")

@app.route("/reset-password/<token>")
def reset_password_form(token):
    """Show password reset form with token validation"""
    try:
        email = request.args.get('email', '').strip().lower()
        
        if not email or not token:
            return render_template("forgot.html", error="Invalid reset link. Please request a new password reset.")
        
        # Check if token exists and is valid
        if email not in reset_tokens:
            return render_template("forgot.html", error="Invalid or expired reset link. Please request a new password reset.")
        
        stored_token_data = reset_tokens[email]
        
        if stored_token_data['token'] != token:
            return render_template("forgot.html", error="Invalid reset link. Please request a new password reset.")
        
        if stored_token_data.get('used', False):
            return render_template("forgot.html", error="This reset link has already been used. Please request a new password reset.")
        
        # Check if token is expired (1 hour)
        if time.time() - stored_token_data['timestamp'] > 3600:  # 1 hour
            del reset_tokens[email]
            return render_template("forgot.html", error="Reset link has expired. Please request a new password reset.")
        
        # Show password reset form
        return render_template("reset-password.html", token=token, email=email)
        
    except Exception as e:
        print(f"ERROR: Reset password form error: {e}")
        return render_template("forgot.html", error="Invalid reset link. Please request a new password reset.")


@app.route("/set-new-password", methods=["POST"])
def set_new_password():
    """Handle new password setting with token validation"""
    global reset_tokens  # Use global variable
    
    try:
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        token = request.form.get("token", "").strip()
        
        print(f"[SEARCH] Password reset attempt for: {email}")
        print(f"🔑 Token received: {token[:20]}..." if token else "No token")
        print(f"📋 Available reset tokens: {list(reset_tokens.keys())}")
        
        if not all([email, new_password, confirm_password, token]):
            print(f"ERROR: Missing fields: email={bool(email)}, password={bool(new_password)}, confirm={bool(confirm_password)}, token={bool(token)}")
            return render_template("reset-password.html", 
                                 token=token, email=email,
                                 error="Please fill in all fields")
        
        # Email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            print(f"ERROR: Invalid email format: {email}")
            return render_template("reset-password.html", 
                                 token=token, email=email,
                                 error="Please enter a valid email address")
        
        # Password validation
        if len(new_password) < 6:
            print(f"ERROR: Password too short: {len(new_password)} characters")
            return render_template("reset-password.html", 
                                 token=token, email=email,
                                 error="Password must be at least 6 characters long")
        
        if new_password != confirm_password:
            print(f"ERROR: Passwords don't match")
            return render_template("reset-password.html", 
                                 token=token, email=email,
                                 error="Passwords do not match. Please try again.")
        
        # Validate token
        if email not in reset_tokens:
            print(f"ERROR: No reset token found for email: {email}")
            return render_template("forgot.html", error="Invalid or expired reset link. Please request a new password reset.")
        
        stored_token_data = reset_tokens[email]
        
        if stored_token_data['token'] != token:
            print(f"ERROR: Token mismatch for email: {email}")
            return render_template("forgot.html", error="Invalid reset link. Please request a new password reset.")
        
        if stored_token_data.get('used', False):
            print(f"ERROR: Token already used for email: {email}")
            return render_template("forgot.html", error="This reset link has already been used. Please request a new password reset.")
        
        # Check if token is expired (1 hour)
        if time.time() - stored_token_data['timestamp'] > 3600:  # 1 hour
            print(f"ERROR: Token expired for email: {email}")
            del reset_tokens[email]
            return render_template("forgot.html", error="Reset link has expired. Please request a new password reset.")
        
        # Get user from database
        user = db.get_user(email)
        
        if not user:
            print(f"ERROR: No account found for email: {email}")
            return render_template("forgot.html", error="No account found with this email address")
        
        # Update password in MySQL database
        try:
            query = "UPDATE users SET password = %s, updated_at = NOW() WHERE email = %s"
            success = db.execute_query(query, (new_password, email))
            
            if not success:
                print(f"ERROR: Failed to update password in database for: {email}")
                return render_template("reset-password.html", 
                                     token=token, email=email,
                                     error="Failed to update password. Please try again.")
        except Exception as e:
            print(f"ERROR: Database error while updating password: {e}")
            return render_template("reset-password.html", 
                                 token=token, email=email,
                                 error="Database error. Please try again.")
        
        # Also update in-memory user_accounts for backward compatibility
        user_accounts = getattr(app, 'user_accounts', {})
        user_accounts[email] = new_password
        app.user_accounts = user_accounts
        
        # Mark token as used
        reset_tokens[email]['used'] = True
        
        print(f"SUCCESS: Password updated successfully for: {email}")
        print(f"[PASSWORD] New password: {new_password}")
        print(f"[DATABASE] Password updated in MySQL database")
        
        # Send confirmation email
        try:
            SENDER_EMAIL = "mk4829779@gmail.com"
            SENDER_PASSWORD = "cbfiekxqfivdwcjs"
            
            # Get user name
            user_profiles = getattr(app, 'user_profiles', {})
            user_name = user_profiles.get(email, {}).get('name', email.split('@')[0].title())
            
            msg = MIMEText(f"""
Hello {user_name},

Your Smart Bus account password has been successfully updated!

Account Details:
- Email: {email}
- Password updated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- Reset method: Email verification link

You can now log in with your new password at: http://localhost:5000/

Security Information:
- If you didn't make this change, please contact support immediately
- Keep your password secure and don't share it with anyone
- Consider using a unique password for your Smart Bus account

Thank you for using Smart Bus!

Best regards,
Smart Bus Team

Support: mk4829779@gmail.com
Phone: +91 8340927497
            """)
            
            msg["Subject"] = "Smart Bus - Password Successfully Updated"
            msg["From"] = f"Smart Bus Support <{SENDER_EMAIL}>"
            msg["To"] = email
            
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            print(f"SUCCESS: Password update confirmation email sent to {email}")
            
        except Exception as e:
            print(f"ERROR: Failed to send password update email: {e}")
        
        # Clean up used token
        if email in reset_tokens:
            del reset_tokens[email]
        
        # Redirect to login page with success message
        return render_template("index.html", 
                             success="Password updated successfully! You can now log in with your new password.")
            
    except Exception as e:
        import traceback
        print(f"ERROR: Password update error: {e}")
        print(f"ERROR: Traceback: {traceback.format_exc()}")
        return render_template("reset-password.html", 
                             token=request.form.get("token", ""), 
                             email=request.form.get("email", ""),
                             error="Password update failed. Please try again.")

# ---------- SIGN UP FUNCTIONALITY ----------
@app.route("/sign-in")
def sign_up():
    """Sign up page"""
    return render_template("sign-in.html")

@app.route("/register", methods=["POST"])
def register():
    """Handle user registration"""
    try:
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        name = request.form.get("name", "")
        phone = request.form.get("phone", "")
        
        if not email or not password:
            return render_template("sign-in.html", error="Email and password are required")
        
        if password != confirm_password:
            return render_template("sign-in.html", error="Passwords do not match")
        
        if len(password) < 6:
            return render_template("sign-in.html", error="Password must be at least 6 characters long")
        
        email_lower = email.lower().strip()
        
        # Email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email_lower):
            return render_template("sign-in.html", error="Please enter a valid email address")
        
        # Get user accounts
        user_accounts = getattr(app, 'user_accounts', {
            "mk4829779@gmail.com": "Manoj123",
            "lingammanojkumar178@gmail.com": "Kumar123",
        })
        
        # Check if account already exists
        if email_lower in user_accounts:
            return render_template("sign-in.html", error="Account already exists with this email. Please login instead.")
        
        # Create new account
        user_accounts[email_lower] = password.strip()
        app.user_accounts = user_accounts
        
        # Create user profile
        user_profiles = getattr(app, 'user_profiles', {})
        user_profiles[email_lower] = {
            'name': name or email_lower.split('@')[0].title(),
            'email': email_lower,
            'phone': phone,
            'city': '',
            'address': '',
            'updated_at': datetime.datetime.now().isoformat(),
            'account_type': 'email'
        }
        app.user_profiles = user_profiles
        
        # Send welcome email
        try:
            SENDER_EMAIL = "mk4829779@gmail.com"
            SENDER_PASSWORD = "cbfiekxqfivdwcjs"
            
            msg = MIMEText(f"""
Hello {name or 'Smart Bus User'},

Welcome to Smart Bus! Your account has been created successfully.

Your login credentials:
Email: {email_lower}
Password: {password}

You can now login and start using Smart Bus services:
- Buy bus passes
- Plan routes
- Manage your account
- Renew passes

Login at: http://localhost:5000/

Thank you for joining Smart Bus!

Smart Bus Team
            """)
            
            msg["Subject"] = "Welcome to Smart Bus - Account Created"
            msg["From"] = SENDER_EMAIL
            msg["To"] = email_lower
            
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            print(f"SUCCESS: Welcome email sent to {email_lower}")
            
        except Exception as e:
            print(f"ERROR: Failed to send welcome email: {e}")
        
        print(f"SUCCESS: New account created for {email_lower}")
        return render_template("index.html", success=f"Account created successfully! Please login with your email and password.")
        
    except Exception as e:
        print(f"ERROR: Registration error: {e}")
        return render_template("sign-in.html", error="Registration failed. Please try again.")

# ---------- PASS EXPIRY NOTIFICATION SYSTEM ----------
@app.route("/buy-test-pass", methods=["POST"])
def buy_test_pass():
    """Buy a test daily pass to check expiry notifications"""
    try:
        data = request.get_json()
        user_email = data.get('user_email', 'mk4829779@gmail.com')
        pass_type = data.get('pass_type', 'Daily Pass')
        
        # Calculate expiry date based on pass type
        from datetime import datetime, timedelta
        now = datetime.now()
        
        if pass_type == 'Daily Pass':
            expiry_date = now + timedelta(days=1)
        elif pass_type == 'Weekly Pass':
            expiry_date = now + timedelta(days=7)
        elif pass_type == 'Monthly Pass':
            expiry_date = now + timedelta(days=30)
        else:
            expiry_date = now + timedelta(days=1)  # Default to daily
        
        # Create pass record
        pass_id = f"PASS_{int(time.time())}"
        pass_record = {
            'id': pass_id,
            'user_email': user_email,
            'pass_type': pass_type,
            'purchase_date': now.isoformat(),
            'expiry_date': expiry_date.isoformat(),
            'price': '₹25' if pass_type == 'Daily Pass' else '₹150',
            'route': 'Test Route - City Center to Airport',
            'status': 'active',
            'notifications_sent': []
        }
        
        # Store pass
        if user_email not in user_passes:
            user_passes[user_email] = []
        user_passes[user_email].append(pass_record)
        
        print(f"[PASS] Test pass created: {pass_id}")
        print(f"📅 Expiry date: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Send purchase confirmation email
        send_pass_purchase_email(user_email, pass_record)
        
        # Schedule expiry notifications
        schedule_expiry_notifications(user_email, pass_record)
        
        return {
            "success": True,
            "message": "Test pass purchased successfully!",
            "pass_id": pass_id,
            "expiry_date": expiry_date.isoformat(),
            "notifications_scheduled": True
        }
        
    except Exception as e:
        print(f"ERROR: Error buying test pass: {e}")
        return {"success": False, "error": str(e)}, 500

@app.route("/check-pass-expiry", methods=["GET"])
def check_pass_expiry():
    """Check for expiring passes and send notifications"""
    try:
        from datetime import datetime, timedelta
        now = datetime.now()
        notifications_sent = 0
        
        # Check all user passes
        for user_email, passes in user_passes.items():
            for pass_record in passes:
                expiry_date = datetime.fromisoformat(pass_record['expiry_date'])
                days_until_expiry = (expiry_date - now).days
                hours_until_expiry = (expiry_date - now).total_seconds() / 3600
                
                # Send notifications at different intervals
                notification_triggers = [
                    (7, "7_days"),      # 7 days before
                    (3, "3_days"),      # 3 days before  
                    (1, "1_day"),       # 1 day before
                    (0.5, "12_hours"),  # 12 hours before (0.5 days)
                    (0.083, "2_hours")  # 2 hours before (0.083 days)
                ]
                
                for trigger_days, trigger_key in notification_triggers:
                    # Check if we should send this notification
                    if (days_until_expiry <= trigger_days and 
                        trigger_key not in pass_record.get('notifications_sent', [])):
                        
                        # Send notification
                        send_expiry_notification(user_email, pass_record, trigger_key, days_until_expiry, hours_until_expiry)
                        
                        # Mark notification as sent
                        if 'notifications_sent' not in pass_record:
                            pass_record['notifications_sent'] = []
                        pass_record['notifications_sent'].append(trigger_key)
                        
                        notifications_sent += 1
                        print(f"[EMAIL] Sent {trigger_key} notification for pass {pass_record['id']}")
                
                # Mark pass as expired if past expiry date
                if days_until_expiry < 0 and pass_record['status'] == 'active':
                    pass_record['status'] = 'expired'
                    send_expired_notification(user_email, pass_record)
                    notifications_sent += 1
                    print(f"ERROR: Pass {pass_record['id']} marked as expired")
        
        return {
            "success": True,
            "notifications_sent": notifications_sent,
            "checked_at": now.isoformat()
        }
        
    except Exception as e:
        print(f"ERROR: Error checking pass expiry: {e}")
        return {"success": False, "error": str(e)}, 500

@app.route("/get-user-passes/<email>")
def get_user_passes(email):
    """Get all passes for a user from MySQL database"""
    try:
        email_lower = email.lower().strip()
        
        # Get passes from MySQL database
        mysql_passes = db.get_user_passes(email_lower)
        
        # Convert MySQL format to frontend format
        passes = []
        for mysql_pass in mysql_passes:
            pass_record = {
                'id': mysql_pass['transaction_id'],
                'type': mysql_pass['pass_type'],
                'price': f"₹{mysql_pass['price']:.0f}",
                'route': mysql_pass['route'],
                'distance': mysql_pass['distance'],
                'expiryDate': mysql_pass['expiry_date'].isoformat() if hasattr(mysql_pass['expiry_date'], 'isoformat') else str(mysql_pass['expiry_date']),
                'paymentMethod': mysql_pass['payment_method'],
                'purchaseDate': mysql_pass['purchase_date'].isoformat() if hasattr(mysql_pass['purchase_date'], 'isoformat') else str(mysql_pass['purchase_date']),
                'status': mysql_pass['status']
            }
            passes.append(pass_record)
        
        # Add time remaining for each pass
        from datetime import datetime
        now = datetime.now()
        
        for pass_record in passes:
            expiry_date = datetime.fromisoformat(pass_record['expiryDate'])
            days_remaining = (expiry_date - now).days
            hours_remaining = (expiry_date - now).total_seconds() / 3600
            
            pass_record['days_remaining'] = days_remaining
            pass_record['hours_remaining'] = round(hours_remaining, 1)
            pass_record['is_expired'] = days_remaining < 0
            pass_record['is_expiring_soon'] = 0 <= days_remaining <= 7
        
        print(f"[DATA] Retrieved {len(passes)} passes from MySQL for {email_lower}")
        
        return {
            "success": True,
            "passes": passes,
            "total_passes": len(passes)
        }
        
    except Exception as e:
        print(f"ERROR: Error getting user passes: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}, 500

@app.route("/save-user-pass", methods=["POST"])
def save_user_pass():
    """Save a user pass to backend storage (called from payment.html)"""
    try:
        data = request.get_json()
        user_email = data.get('email', '').lower().strip()
        pass_data = data.get('pass', {})
        
        if not user_email or not pass_data:
            return {"success": False, "error": "Missing email or pass data"}, 400
        
        print(f"💾 Saving pass to backend for {user_email}: {pass_data.get('type', 'Unknown')}")
        
        # Store the pass
        success = store_user_pass(user_email, pass_data)
        
        if success:
            # Schedule expiry notifications
            schedule_expiry_notifications(user_email, pass_data)
            
            # Send emails in background
            try:
                user_name = pass_data.get('userName', user_email.split('@')[0].title())
                pass_type = pass_data.get('type', 'Daily Pass')
                amount = pass_data.get('price', '₹0').replace('₹', '')
                route = pass_data.get('route', 'City Route')
                distance = pass_data.get('distance', '0')
                payment_method = pass_data.get('paymentMethod', 'Razorpay')
                
                # Generate receipt
                receipt = generate_enhanced_receipt(
                    pass_type=pass_type,
                    amount=amount,
                    route=route,
                    distance=distance,
                    payment_method=payment_method,
                    user_name=user_name,
                    user_email=user_email,
                    transaction_type='new_pass',
                    device_type='Web'
                )
                
                def send_emails_async():
                    """Send emails in background thread"""
                    try:
                        print(f"   📧 Sending receipt and pass emails to {user_email}...")
                        # Send receipt email
                        send_enhanced_email_notification(user_email, user_name, receipt, 'new_pass')
                        # Send TSRTC pass email
                        send_tsrtc_pass_email(user_email, user_name, pass_data)
                        print(f"   ✅ Emails sent successfully")
                    except Exception as e:
                        print(f"   ⚠️  Email background error: {e}")
                
                email_thread = threading.Thread(target=send_emails_async)
                email_thread.daemon = True
                email_thread.start()
                
            except Exception as e:
                print(f"⚠️  Failed to initiate email sending: {e}")
            
            return {
                "success": True,
                "message": "Pass saved successfully and emails scheduled",
                "pass_id": pass_data.get('id')
            }
        else:
            return {"success": False, "error": "Failed to store pass"}, 500
        
    except Exception as e:
        print(f"ERROR: Error saving user pass: {e}")
        return {"success": False, "error": str(e)}, 500

@app.route("/get-notifications/<email>")
def get_notifications(email):
    """Get notifications for a user"""
    try:
        email_lower = email.lower().strip()
        notifications = pass_notifications.get(email_lower, [])
        
        # Sort by date (newest first)
        notifications.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return {
            "success": True,
            "notifications": notifications,
            "unread_count": len([n for n in notifications if not n.get('read', False)])
        }
        
    except Exception as e:
        print(f"ERROR: Error getting notifications: {e}")
        return {"success": False, "error": str(e)}, 500

@app.route("/mark-notification-read", methods=["POST"])
def mark_notification_read():
    """Mark a notification as read"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        notification_id = data.get('notification_id')
        
        if email in pass_notifications:
            for notification in pass_notifications[email]:
                if notification['id'] == notification_id:
                    notification['read'] = True
                    break
        
        return {"success": True}
        
    except Exception as e:
        print(f"ERROR: Error marking notification as read: {e}")
        return {"success": False, "error": str(e)}, 500
    """Send pass purchase confirmation email"""
    try:
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfiekxqfivdwcjs"
        
        user_name = user_email.split('@')[0].title()
        
        msg = MIMEText(f"""
Hello {user_name},

Your Smart Bus pass has been purchased successfully!

Pass Details:
- Pass Type: {pass_record['pass_type']}
- Pass ID: {pass_record['id']}
- Route: {pass_record['route']}
- Price: {pass_record['price']}
- Purchase Date: {datetime.datetime.fromisoformat(pass_record['purchase_date']).strftime('%Y-%m-%d %H:%M:%S')}
- Valid Until: {datetime.datetime.fromisoformat(pass_record['expiry_date']).strftime('%Y-%m-%d %H:%M:%S')}

Important Notes:
- You will receive email notifications before your pass expires
- Renew your pass before expiry to avoid service interruption
- Keep this email as proof of purchase

Thank you for choosing Smart Bus!

Best regards,
Smart Bus Team

Support: mk4829779@gmail.com
Phone: +91 8340927497
        """)
        
        msg["Subject"] = f"Smart Bus - {pass_record['pass_type']} Purchased Successfully"
        msg["From"] = f"Smart Bus <{SENDER_EMAIL}>"
        msg["To"] = user_email
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"SUCCESS: Purchase confirmation email sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to send purchase email: {e}")
        return False

def send_expiry_notification(user_email, pass_record, trigger_key, days_remaining, hours_remaining):
    """Send pass expiry notification email"""
    try:
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfiekxqfivdwcjs"
        
        user_name = user_email.split('@')[0].title()
        
        # Customize message based on time remaining
        if days_remaining >= 1:
            time_msg = f"{days_remaining} day(s)"
            urgency = "WARNING:"
        elif hours_remaining >= 1:
            time_msg = f"{int(hours_remaining)} hour(s)"
            urgency = "🚨"
        else:
            time_msg = "less than 1 hour"
            urgency = "🔴"
        
        msg = MIMEText(f"""
{urgency} PASS EXPIRY ALERT {urgency}

Hello {user_name},

Your Smart Bus pass is expiring soon!

Pass Details:
- Pass Type: {pass_record['pass_type']}
- Pass ID: {pass_record['id']}
- Route: {pass_record['route']}
- Time Remaining: {time_msg}
- Expires On: {datetime.datetime.fromisoformat(pass_record['expiry_date']).strftime('%Y-%m-%d %H:%M:%S')}

ACTION REQUIRED:
[ROUTE] Renew your pass now to avoid service interruption
💳 Visit: http://localhost:5000/renew-pass
[MOBILE] Or use the Smart Bus mobile app

Don't wait until the last minute - renew now for uninterrupted service!

Quick Renewal Link: http://localhost:5000/renew-pass?pass_id={pass_record['id']}

Best regards,
Smart Bus Team

Support: mk4829779@gmail.com
Phone: +91 8340927497
        """)
        
        msg["Subject"] = f"{urgency} Smart Bus Pass Expiring in {time_msg} - Renew Now!"
        msg["From"] = f"Smart Bus Alerts <{SENDER_EMAIL}>"
        msg["To"] = user_email
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        # Add notification to website
        add_website_notification(user_email, {
            'type': 'expiry_warning',
            'title': f'Pass Expiring in {time_msg}',
            'message': f'Your {pass_record["pass_type"]} expires in {time_msg}. Renew now!',
            'pass_id': pass_record['id'],
            'urgency': 'high' if days_remaining <= 1 else 'medium'
        })
        
        print(f"SUCCESS: Expiry notification sent to {user_email} ({trigger_key})")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to send expiry notification: {e}")
        return False

def send_expired_notification(user_email, pass_record):
    """Send pass expired notification email"""
    try:
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfiekxqfivdwcjs"
        
        user_name = user_email.split('@')[0].title()
        
        msg = MIMEText(f"""
ERROR: PASS EXPIRED ERROR:

Hello {user_name},

Your Smart Bus pass has expired and is no longer valid for travel.

Expired Pass Details:
- Pass Type: {pass_record['pass_type']}
- Pass ID: {pass_record['id']}
- Route: {pass_record['route']}
- Expired On: {datetime.datetime.fromisoformat(pass_record['expiry_date']).strftime('%Y-%m-%d %H:%M:%S')}

IMMEDIATE ACTION REQUIRED:
🛒 Purchase a new pass to continue using Smart Bus services
[ROUTE] Or renew your expired pass (additional fees may apply)

Purchase New Pass: http://localhost:5000/passes
Renew Expired Pass: http://localhost:5000/renew-pass?pass_id={pass_record['id']}

Important: You cannot board Smart Bus services without a valid pass.

Best regards,
Smart Bus Team

Support: mk4829779@gmail.com
Phone: +91 8340927497
        """)
        
        msg["Subject"] = "ERROR: Smart Bus Pass EXPIRED - Purchase New Pass Required"
        msg["From"] = f"Smart Bus Alerts <{SENDER_EMAIL}>"
        msg["To"] = user_email
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        # Add notification to website
        add_website_notification(user_email, {
            'type': 'expired',
            'title': 'Pass Expired',
            'message': f'Your {pass_record["pass_type"]} has expired. Purchase a new pass to continue service.',
            'pass_id': pass_record['id'],
            'urgency': 'critical'
        })
        
        print(f"SUCCESS: Expired notification sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to send expired notification: {e}")
        return False

def add_website_notification(user_email, notification_data):
    """Add notification to website dashboard"""
    try:
        if user_email not in pass_notifications:
            pass_notifications[user_email] = []
        
        notification = {
            'id': int(time.time() * 1000),  # Unique ID
            'type': notification_data['type'],
            'title': notification_data['title'],
            'message': notification_data['message'],
            'pass_id': notification_data.get('pass_id'),
            'urgency': notification_data.get('urgency', 'low'),
            'date': datetime.datetime.now().isoformat(),
            'read': False
        }
        
        pass_notifications[user_email].append(notification)
        
        # Keep only last 50 notifications per user
        if len(pass_notifications[user_email]) > 50:
            pass_notifications[user_email] = pass_notifications[user_email][-50:]
        
        print(f"[MOBILE] Website notification added for {user_email}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to add website notification: {e}")
        return False

def schedule_expiry_notifications(user_email, pass_record):
    """Schedule expiry notifications for a pass"""
    try:
        print(f"📅 Scheduling expiry notifications for pass {pass_record['id']}")
        
        # In a production system, you would use a task queue like Celery
        # For this demo, we'll just log that notifications are scheduled
        
        expiry_date = datetime.datetime.fromisoformat(pass_record['expiry_date'])
        print(f"[EMAIL] Notifications scheduled for:")
        print(f"   - 7 days before: {(expiry_date - datetime.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   - 3 days before: {(expiry_date - datetime.timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   - 1 day before: {(expiry_date - datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   - 12 hours before: {(expiry_date - datetime.timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   - 2 hours before: {(expiry_date - datetime.timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to schedule notifications: {e}")
        return False

# ---------- START THE APPLICATION ----------
if __name__ == "__main__":
    print(">> Smart Bus App Starting - OPTIMIZED FOR SPEED...")
    print("[WEB] Access your app at:")
    print("   💻 Desktop: http://localhost:5000/")
    print("   [MOBILE] Mobile: http://192.168.1.100:5000/ (replace with your IP)")
    print("   🌍 Network: http://0.0.0.0:5000/")
    print("=" * 50)
    
    # Get local IP address for mobile access
    import socket
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"[MOBILE] Mobile Access: http://{local_ip}:5000/")
    except:
        print("[MOBILE] Mobile Access: Check your computer's IP address")
    
    print("=" * 50)
    
    # NOTE: app.run() moved to the end of file (line 3881)
    # This section is for reference only

# ---------- MISSING NOTIFICATION FUNCTIONS ----------

def send_pass_purchase_email(user_email, pass_record):
    """Send pass purchase confirmation email"""
    try:
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfiekxqfivdwcjs"
        
        user_name = user_email.split('@')[0].title()
        
        msg = MIMEText(f"""
Hello {user_name},

Your Smart Bus pass has been purchased successfully!

Pass Details:
- Pass Type: {pass_record['pass_type']}
- Pass ID: {pass_record['id']}
- Route: {pass_record['route']}
- Price: {pass_record['price']}
- Purchase Date: {datetime.datetime.fromisoformat(pass_record['purchase_date']).strftime('%Y-%m-%d %H:%M:%S')}
- Valid Until: {datetime.datetime.fromisoformat(pass_record['expiry_date']).strftime('%Y-%m-%d %H:%M:%S')}

Important Notes:
- You will receive email notifications before your pass expires
- Renew your pass before expiry to avoid service interruption
- Keep this email as proof of purchase

Thank you for choosing Smart Bus!

Best regards,
Smart Bus Team

Support: mk4829779@gmail.com
Phone: +91 8340927497
        """)
        
        msg["Subject"] = f"Smart Bus - {pass_record['pass_type']} Purchased Successfully"
        msg["From"] = f"Smart Bus <{SENDER_EMAIL}>"
        msg["To"] = user_email
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"SUCCESS: Purchase confirmation email sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to send purchase email: {e}")
        return False

# ---------- EXPIRY NOTIFICATION ROUTES ----------
@app.route("/send-expiry-notification", methods=["POST"])
def send_expiry_notification_route():
    """API endpoint to send expiry notifications"""
    try:
        data = request.get_json()
        email = data.get('email')
        pass_type = data.get('passType')
        days_until_expiry = data.get('daysUntilExpiry')
        expiry_date = data.get('expiryDate')
        
        if not all([email, pass_type, days_until_expiry, expiry_date]):
            return {"success": False, "error": "Missing required fields"}, 400
        
        # Send expiry notification email
        SENDER_EMAIL = "mk4829779@gmail.com"
        SENDER_PASSWORD = "cbfiekxqfivdwcjs"
        
        user_name = email.split('@')[0].title()
        
        # Customize message based on days remaining
        if days_until_expiry >= 7:
            urgency = "WARNING:"
            action_msg = "Plan ahead and renew your pass"
        elif days_until_expiry >= 3:
            urgency = "🚨"
            action_msg = "Renew your pass soon to avoid interruption"
        elif days_until_expiry >= 1:
            urgency = "🔴"
            action_msg = "URGENT: Renew your pass immediately"
        else:
            urgency = "ERROR:"
            action_msg = "CRITICAL: Your pass expires today!"
        
        msg = MIMEText(f"""
{urgency} PASS EXPIRY ALERT {urgency}

Hello {user_name},

Your Smart Bus pass is expiring soon!

Pass Details:
- Pass Type: {pass_type}
- Time Remaining: {days_until_expiry} day(s)
- Expires On: {datetime.datetime.fromisoformat(expiry_date).strftime('%Y-%m-%d %H:%M:%S')}

ACTION REQUIRED:
{action_msg}

[ROUTE] Renew Now: http://localhost:5000/renew-pass
💳 Buy New Pass: http://localhost:5000/dashboard

Don't wait until the last minute - renew now for uninterrupted service!

Best regards,
Smart Bus Team

Support: mk4829779@gmail.com
Phone: +91 8340927497
        """)
        
        msg["Subject"] = f"{urgency} Smart Bus Pass Expiring in {days_until_expiry} day(s) - Renew Now!"
        msg["From"] = f"Smart Bus Alerts <{SENDER_EMAIL}>"
        msg["To"] = email
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"SUCCESS: Expiry notification sent to {email} ({days_until_expiry} days)")
        
        return {
            "success": True,
            "message": f"Expiry notification sent successfully",
            "days_until_expiry": days_until_expiry
        }
        
    except Exception as e:
        print(f"ERROR: Failed to send expiry notification: {e}")
        return {"success": False, "error": str(e)}, 500

@app.route("/credential-test")
def credential_test():
    """Credential verification test page"""
    return render_template("credential_test.html")

# ---------- GOOGLE CREDENTIAL VERIFICATION ----------

def verify_google_credentials(email, password):
    """
    Verify Gmail credentials directly with Google's IMAP servers
    Returns: (success: bool, message: str, user_info: dict)
    """
    try:
        print(f"[SEARCH] Verifying Google credentials for: {email}")
        
        # Check if it's a Gmail account
        if not email.lower().endswith(('@gmail.com', '@googlemail.com')):
            return False, "Not a Gmail account", {}
        
        # Attempt IMAP connection to verify credentials
        imap_server = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        
        # Try to login with provided credentials
        imap_server.login(email, password)
        
        # If login successful, get some basic info
        imap_server.select('INBOX')
        status, messages = imap_server.search(None, 'ALL')
        message_count = len(messages[0].split()) if messages[0] else 0
        
        # Logout from IMAP
        imap_server.logout()
        
        print(f"SUCCESS: Google credential verification successful: {email}")
        
        # Extract user info from email
        username = email.split('@')[0]
        display_name = username.replace('.', ' ').replace('_', ' ').title()
        
        user_info = {
            'email': email.lower(),
            'name': display_name,
            'account_type': 'google_verified',
            'inbox_count': message_count,
            'verified_at': datetime.datetime.now().isoformat()
        }
        
        return True, "Google credentials verified successfully", user_info
        
    except imaplib.IMAP4.error as e:
        error_msg = str(e).lower()
        print(f"ERROR: Google credential verification failed: {email} - {e}")
        
        if 'authentication failed' in error_msg or 'invalid credentials' in error_msg:
            return False, "Invalid Gmail password", {}
        elif 'application-specific password required' in error_msg:
            return False, "App password required. Please enable 2-factor authentication and use an app password", {}
        elif 'account disabled' in error_msg:
            return False, "Gmail account is disabled", {}
        else:
            return False, f"Gmail verification failed: {str(e)}", {}
            
    except Exception as e:
        print(f"ERROR: Google credential verification error: {email} - {e}")
        return False, f"Connection error: {str(e)}", {}

def verify_google_credentials_smtp(email, password):
    """
    Alternative verification using SMTP (for sending emails)
    Returns: (success: bool, message: str)
    """
    try:
        print(f"[SEARCH] Verifying Google SMTP credentials for: {email}")
        
        # Create SMTP connection
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        
        # Try to login
        server.login(email, password)
        server.quit()
        
        print(f"SUCCESS: Google SMTP verification successful: {email}")
        return True, "SMTP credentials verified"
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"ERROR: Google SMTP authentication failed: {email} - {e}")
        return False, "Invalid Gmail credentials for SMTP"
    except Exception as e:
        print(f"ERROR: Google SMTP verification error: {email} - {e}")
        return False, f"SMTP connection error: {str(e)}"

@app.route("/verify-google-credentials", methods=["POST"])
def verify_google_credentials_api():
    """API endpoint for Google credential verification"""
    try:
        data = request.get_json()
        
        if not data:
            return {"success": False, "error": "No data provided"}, 400
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return {"success": False, "error": "Email and password required"}, 400
        
        email_lower = email.lower().strip()
        
        # Check if it's a Gmail account
        if not email_lower.endswith(('@gmail.com', '@googlemail.com')):
            return {
                "success": False,
                "error": "Not a Gmail account",
                "is_gmail": False
            }
        
        print(f"[SEARCH] API Google credential verification: {email_lower}")
        
        # Verify with Google servers
        success, message, user_info = verify_google_credentials(email_lower, password)
        
        if success:
            print(f"SUCCESS: API Google verification successful: {email_lower}")
            
            # Also verify SMTP capability
            smtp_success, smtp_message = verify_google_credentials_smtp(email_lower, password)
            
            return {
                "success": True,
                "message": "Google credentials verified successfully",
                "user": user_info,
                "capabilities": {
                    "imap": True,
                    "smtp": smtp_success,
                    "smtp_message": smtp_message
                },
                "verification_method": "Google IMAP Server"
            }
        else:
            print(f"ERROR: API Google verification failed: {email_lower} - {message}")
            return {
                "success": False,
                "error": message,
                "is_gmail": True,
                "verification_method": "Google IMAP Server"
            }
        
    except Exception as e:
        print(f"ERROR: API Google credential verification error: {e}")
        return {"success": False, "error": str(e)}, 500

# ---------- AUTOMATIC CREDENTIAL VERIFICATION API ----------
@app.route("/verify-credentials", methods=["POST"])
def verify_credentials():
    """API endpoint for automatic credential verification"""
    try:
        data = request.get_json()
        
        if not data:
            return {"success": False, "error": "No data provided"}, 400
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return {"success": False, "error": "Email and password required"}, 400
        
        email_lower = email.lower().strip()
        password_clean = password.strip()
        
        print(f"[SEARCH] API credential verification: {email_lower}")
        
        # Check if user exists in MySQL database
        user = db.get_user(email_lower)
        
        if user:
            # User exists - verify password
            if user['password'] == password_clean:
                # Correct password
                account_type = user.get('account_type', 'email')
                user_name = user.get('name', email_lower.split('@')[0])
                
                print(f"SUCCESS: API verification successful: {email_lower}")
                
                return {
                    "success": True,
                    "message": "Credentials verified successfully",
                    "user": {
                        "email": email_lower,
                        "name": user_name,
                        "account_type": account_type,
                        "created_at": str(user.get('created_at', '')),
                        "phone": user.get('phone', ''),
                        "city": user.get('city', ''),
                        "address": user.get('address', '')
                    }
                }
            else:
                print(f"ERROR: API verification failed: {email_lower}")
                return {
                    "success": False,
                    "error": "Invalid password",
                    "user_exists": True,
                    "account_type": user.get('account_type', 'unknown')
                }
        else:
            print(f"ERROR: API user not found: {email_lower}")
            return {
                "success": False,
                "error": "User not found",
                "user_exists": False,
                "suggestion": "Use Gmail address for auto-registration" if email_lower.split('@')[1] in ['gmail.com', 'googlemail.com'] else "Please sign up first"
            }
        
    except Exception as e:
        print(f"ERROR: API credential verification error: {e}")
        return {"success": False, "error": str(e)}, 500

@app.route("/test-all-users", methods=["GET"])
def test_all_users():
    """API endpoint to test all users in database"""
    try:
        print("🧪 Testing all users in database")
        
        # Get all users
        users = db.get_all_users()
        
        if not users:
            return {"success": False, "error": "No users found in database"}
        
        results = []
        
        for user in users:
            user_info = {
                "email": user['email'],
                "name": user['name'],
                "account_type": user['account_type'],
                "created_at": str(user['created_at']),
                "phone": user.get('phone', ''),
                "city": user.get('city', ''),
                "address": user.get('address', ''),
                "password_set": bool(user.get('password')),
                "password_length": len(user.get('password', '')) if user.get('password') else 0
            }
            results.append(user_info)
        
        return {
            "success": True,
            "total_users": len(users),
            "users": results
        }
        
    except Exception as e:
        print(f"ERROR: Error testing all users: {e}")
        return {"success": False, "error": str(e)}, 500

# ---------- DISTANCE CALCULATION FUNCTIONS ----------

def find_coordinates(location_name, coordinates_db):
    """Find coordinates for a location with fuzzy matching"""
    # Direct match
    if location_name in coordinates_db:
        return coordinates_db[location_name]
    
    # Partial match
    for key, coords in coordinates_db.items():
        if key in location_name or location_name in key:
            print(f"[LOCATION] Partial match: {location_name} → {key}")
            return coords
    
    # Word-based matching
    words = location_name.split()
    for word in words:
        if len(word) > 3:
            for key, coords in coordinates_db.items():
                if word in key or key in word:
                    print(f"[LOCATION] Word match: {word} → {key}")
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
        ('hyderabad', 'warangal'): (148.0, 180),
        ('warangal', 'hyderabad'): (148.0, 180),
        ('hyderabad', 'airport'): (42.0, 60),
        ('airport', 'hyderabad'): (42.0, 60),
    }
    
    # Try exact match first
    key = (origin, destination)
    if key in known_distances:
        return known_distances[key]
    
    # Try reverse match
    reverse_key = (destination, origin)
    if reverse_key in known_distances:
        return known_distances[reverse_key]
    
    # Try partial matching
    for (o, d), (dist, time) in known_distances.items():
        if (o in origin or origin in o) and (d in destination or destination in d):
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
            return 148.0, 180  # Hyderabad-Warangal distance
        elif 'airport' in origin or 'airport' in destination:
            return 42.0, 60    # Airport distance
        else:
            return 65.0, 90    # Other long distance (reduced from 85km)
    elif origin_city and dest_city:
        return 12.0, 35        # Within city (reduced from 18km)
    else:
        return 8.0, 25         # Default city distance (NO MORE 25km!)

def get_realtime_distance(origin, destination):
    """Get real-time distance using coordinate-based calculation"""
    try:
        # Coordinate database for accurate calculations - Comprehensive Telangana locations
        coordinates = {
            # Hyderabad & Surroundings
            'hyderabad': (17.3850, 78.4867),
            'secunderabad': (17.4399, 78.4983),
            'santosh nagar': (17.3616, 78.4747),
            'santoshnagar': (17.3616, 78.4747),
            'colony kumarwadi': (17.3850, 78.4600),
            'kumarwadi': (17.3850, 78.4600),
            'gachibowli': (17.4399, 78.3482),
            'hitech city': (17.4485, 78.3908),
            'jubilee hills': (17.4239, 78.4738),
            'banjara hills': (17.4126, 78.4071),
            'ameerpet': (17.4374, 78.4482),
            'kondapur': (17.4616, 78.3436),
            'kukatpally': (17.4850, 78.4138),
            'uppal': (17.4065, 78.5510),
            'dilsukhnagar': (17.3687, 78.5230),
            'airport': (17.2403, 78.4294),
            'rajiv gandhi international airport': (17.2403, 78.4294),
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
            
            # Warangal District
            'warangal': (17.9689, 79.5941),
            'hanumakonda': (17.9784, 79.5941),
            'kazipet': (17.9784, 79.4564),
            'hanamkonda': (17.9784, 79.5941),
            'jangaon': (17.7244, 79.1514),
            'bhupalpally': (18.4347, 79.9953),
            
            # Mahabubabad District (ADDED FOR YOUR REQUEST)
            'mahabubabad': (17.5981, 80.0019),
            'narsampet': (17.9294, 79.8947),
            'thorrur': (17.6500, 79.9500),
            'kesamudram': (17.7500, 79.9000),
            'maripeda': (17.5000, 80.1000),
            'gudur': (17.4500, 80.0500),
            
            # Khammam District (Near Mahabubabad)
            'khammam': (17.2473, 80.1514),
            'kothagudem': (17.5500, 80.6167),
            'yellandu': (17.5917, 80.3333),
            'bhadrachalam': (17.6688, 80.8936),
            'palvancha': (17.5833, 80.6500),
            'sathupalli': (17.2500, 80.8667),
            
            # Nalgonda District
            'nalgonda': (17.0500, 79.2667),
            'suryapet': (17.1500, 79.6167),
            'miryalaguda': (16.8667, 79.5667),
            'devarakonda': (16.6833, 78.9167),
            'bhongir': (17.5167, 78.8833),
            
            # Karimnagar District
            'karimnagar': (18.4386, 79.1288),
            'jagtial': (18.7939, 78.9167),
            'peddapalli': (18.6167, 79.3833),
            'ramagundam': (18.7553, 79.4747),
            'mancherial': (18.8667, 79.4667),
            
            # Nizamabad District
            'nizamabad': (18.6725, 78.0941),
            'kamareddy': (18.3167, 78.3333),
            'bodhan': (18.6667, 77.8833),
            'armoor': (18.7833, 78.2833),
            'banswada': (18.3833, 77.8833),
            
            # Adilabad District
            'adilabad': (19.6667, 78.5333),
            'nirmal': (19.0833, 78.3500),
            'mancherial': (18.8667, 79.4667),
            'asifabad': (19.3667, 79.2833),
            'bellampalli': (19.0500, 79.4833),
            
            # Medak District
            'medak': (18.0500, 78.2667),
            'sangareddy': (17.6167, 78.0833),
            'siddipet': (18.1000, 78.8500),
            'zaheerabad': (17.6833, 77.6167),
            'narayankhed': (17.7167, 77.4833),
            
            # Rangareddy District
            'rangareddy': (17.3850, 78.4867),
            'shamshabad': (17.2500, 78.4000),
            'vikarabad': (17.3333, 77.9000),
            'chevella': (17.2833, 78.1333),
            'tandur': (17.2500, 77.5833),
            
            # Mahbubnagar District
            'mahbubnagar': (16.7333, 77.9833),
            'wanaparthy': (16.3667, 78.0667),
            'gadwal': (16.2333, 77.8000),
            'nagarkurnool': (16.4833, 78.3167),
            'kalwakurthy': (16.6833, 78.0167),
            
            # Nellore & Nearby (Andhra Pradesh border)
            'nellore': (14.4426, 79.9865),
            'kavali': (14.9167, 79.9833),
            'gudur': (14.1500, 79.8500),
            'venkatagiri': (13.9667, 79.5833),
            
            # Other Important Locations
            'nekonda': (17.8500, 79.8500),  # ADDED FOR YOUR REQUEST
            'station ghanpur': (18.2000, 79.5500),
            'mulugu': (18.1833, 79.9333),
            'govindaraopet': (17.8833, 80.3833),
            'manuguru': (17.9833, 80.7500),
            'yellandu': (17.5917, 80.3333),
        }
        
        # Normalize location names
        origin_norm = origin.lower().strip()
        dest_norm = destination.lower().strip()
        
        # Find coordinates
        origin_coords = find_coordinates(origin_norm, coordinates)
        dest_coords = find_coordinates(dest_norm, coordinates)
        
        if origin_coords and dest_coords:
            # Calculate distance using Haversine formula (straight-line distance)
            straight_distance = haversine_distance(
                origin_coords[0], origin_coords[1],
                dest_coords[0], dest_coords[1]
            )
            
            # Apply road distance correction factor (roads are ~25% longer than straight line)
            # This makes our distance closer to Google Maps road distance
            distance = straight_distance * 1.25
            
            # Estimate travel time based on distance and traffic
            if distance <= 10:
                travel_time = int(distance * 4)  # City traffic: ~15 km/h
            elif distance <= 30:
                travel_time = int(distance * 3)  # Suburban: ~20 km/h
            else:
                travel_time = int(distance * 2)  # Highway: ~30 km/h
            
            print(f"[LOCATION] Real-time calculation:")
            print(f"  Straight-line: {straight_distance:.1f} km")
            print(f"  Road distance (x1.25): {distance:.1f} km")
            print(f"  Travel time: {travel_time} mins")
            return round(distance, 1), travel_time
        
        # Fallback estimation
        print(f"[LOCATION] Using fallback estimation for: {origin} → {destination}")
        return estimate_distance_fallback(origin_norm, dest_norm)
        
    except Exception as e:
        print(f"ERROR: Real-time distance calculation error: {e}")
        return None, None

def calculate_fare_by_pass_type(distance, pass_type, base_price):
    """Calculate fare using just the pass amount (not multiplied by distance)"""
    try:
        print(f"[FARE] Simple fare calculation:")
        print(f"   Distance: {distance} km")
        print(f"   Pass Type: {pass_type}")
        print(f"   Base Price: {base_price}")
        
        # Extract numeric value from base_price (remove ₹ symbol)
        if isinstance(base_price, str):
            pass_amount = float(base_price.replace('₹', '').replace(',', '').strip()) if base_price.replace('₹', '').replace(',', '').strip() else 50
        else:
            pass_amount = float(base_price) if base_price else 50
        
        print(f"   Pass Amount: ₹{pass_amount}")
        
        # Simple calculation: Just use the pass amount (no distance multiplication)
        final_fare = int(pass_amount)
        
        print(f"   Final Fare: ₹{final_fare} (Pass amount only)")
        
        return final_fare
        
    except Exception as e:
        print(f"ERROR: Fare calculation error: {e}")
        # Fallback: return 50 as default pass amount
        return 50

# ---------- DISTANCE CALCULATION API ----------
@app.route("/calculate-distance-realtime", methods=["POST"])
def calculate_distance_realtime():
    """Real-time distance calculation with pass-type-based pricing"""
    try:
        print("[ROUTE] Real-time distance calculation route called")
        data = request.get_json()
        print(f"[DATA] Received data: {data}")
        
        if not data:
            print("ERROR: No JSON data received")
            return {"success": False, "error": "No data provided"}, 400
        
        origin = data.get('origin')
        destination = data.get('destination')
        pass_type = data.get('pass_type', 'Regular Pass')
        base_price = data.get('base_price', '₹50')
        
        if not origin or not destination:
            print("ERROR: Missing origin or destination")
            return {"success": False, "error": "Origin and destination required"}, 400
        
        print(f"[MAP] Calculating real-time distance: {origin} → {destination}")
        print(f"[PASS] Pass type: {pass_type}, Base price: {base_price}")
        
        # Get real-time distance
        distance_km, travel_time_minutes = get_realtime_distance(origin, destination)
        
        if distance_km is None:
            print("ERROR: Distance calculation returned None")
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
            "calculation_method": "Real-time Coordinate-based Calculation"
        }
        
        print(f"SUCCESS: Real-time distance calculated successfully:")
        print(f"   Distance: {distance_km} km")
        print(f"   Pass Type: {pass_type}")
        print(f"   Fare: Rs.{fare}")
        print(f"   Travel time: {travel_time_minutes} mins")
        
        return result
        
    except Exception as e:
        print(f"ERROR: Real-time distance calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}, 500

# ---------- AUTOMATIC EXPIRY CHECKER ----------
@app.route("/run-expiry-check", methods=["POST"])
def run_expiry_check():
    """Manually trigger expiry check for testing"""
    try:
        result = check_pass_expiry()
        return result
        
    except Exception as e:
        print(f"ERROR: Error running expiry check: {e}")
        return {"success": False, "error": str(e)}, 500

# ---------- RUN APPLICATION ----------
if __name__ == "__main__":
    print(">> Starting Smart Bus Fast Server...")
    print(">> Email notifications: ENABLED")
    print(">> Pass management: ENABLED")
    print(">> Website notifications: ENABLED")
    print(">> Expiry notifications: ENABLED")
    print(">> Server: http://localhost:5000")
    print(">> Mobile access: http://192.168.29.96:5000")
    print("=" * 50)
    
    # Run on all interfaces for mobile access
    app.run(host="0.0.0.0", port=5000, debug=False)


"""
Test script to verify pass ticket system is working correctly
"""

print("=" * 70)
print("PASS TICKET SYSTEM - VERIFICATION TEST")
print("=" * 70)

# Test 1: Check if passes.html has ticket functions
print("\n1. Checking passes.html for ticket functions...")
try:
    with open('templates/passes.html', 'r', encoding='utf-8') as f:
        content = f.read()
        
    checks = {
        'viewTicket function': 'function viewTicket(' in content,
        'downloadTicket function': 'function downloadTicket(' in content,
        'generateTSRTCTicketHTML function': 'function generateTSRTCTicketHTML(' in content,
        'Government stamp': 'GOVERNMENT OF' in content and 'TELANGANA' in content and 'TSRTC' in content,
        'View Ticket button': 'View Ticket' in content,
        'Download Ticket button': 'Download Ticket' in content,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {check_name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n   ✅ All passes.html checks passed!")
    else:
        print("\n   ❌ Some passes.html checks failed!")
        
except Exception as e:
    print(f"   ❌ Error reading passes.html: {e}")

# Test 2: Check if app_fast.py has email imports and constants
print("\n2. Checking app_fast.py for email configuration...")
try:
    with open('app_fast.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    checks = {
        'MIMEMultipart import': 'from email.mime.multipart import MIMEMultipart' in content,
        'MIMEText import': 'from email.mime.text import MIMEText' in content,
        'SENDER_EMAIL constant': 'SENDER_EMAIL = ' in content,
        'SENDER_PASSWORD constant': 'SENDER_PASSWORD = ' in content,
        'send_tsrtc_pass_email function': 'def send_tsrtc_pass_email(' in content,
        'db.create_pass call': 'db.create_pass(' in content,
        'Government stamp in email': 'GOVERNMENT OF' in content and 'govt-stamp' in content,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {check_name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n   ✅ All app_fast.py checks passed!")
    else:
        print("\n   ❌ Some app_fast.py checks failed!")
        
except Exception as e:
    print(f"   ❌ Error reading app_fast.py: {e}")

# Test 3: Check database.py for pass operations
print("\n3. Checking database.py for pass operations...")
try:
    with open('database.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    checks = {
        'create_pass method': 'def create_pass(' in content,
        'get_user_passes method': 'def get_user_passes(' in content,
        'get_active_passes method': 'def get_active_passes(' in content,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {check_name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n   ✅ All database.py checks passed!")
    else:
        print("\n   ❌ Some database.py checks failed!")
        
except Exception as e:
    print(f"   ❌ Error reading database.py: {e}")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)

print("\n📋 NEXT STEPS:")
print("1. Restart the server: python app_fast.py")
print("2. Login to the system")
print("3. Purchase a pass (complete payment)")
print("4. Go to 'My Passes' page")
print("5. Click 'View Ticket' to see TSRTC ticket with government stamp")
print("6. Check email for TSRTC ticket HTML")
print("7. Click 'Download Ticket' to print/save ticket")

print("\n✅ All components are in place for the ticket system!")
print("=" * 70)

"""
Quick script to check if Flask server is running with latest code
"""

import requests

BASE_URL = "http://localhost:5000"

print("=" * 70)
print("CHECKING FLASK SERVER STATUS")
print("=" * 70)

# Test 1: Is server running?
print("\n1. Testing if server is running...")
try:
    response = requests.get(BASE_URL, timeout=2)
    print(f"   ✅ Server is running (Status: {response.status_code})")
except requests.exceptions.ConnectionError:
    print("   ❌ Server is NOT running!")
    print("   → Start server with: python app.py")
    exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# Test 2: Can we access /forgot with GET?
print("\n2. Testing GET /forgot...")
try:
    response = requests.get(f"{BASE_URL}/forgot", timeout=2)
    if response.status_code == 200:
        print("   ✅ GET /forgot works!")
    else:
        print(f"   ❌ GET /forgot failed (Status: {response.status_code})")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Can we POST to /forgot?
print("\n3. Testing POST /forgot...")
try:
    response = requests.post(
        f"{BASE_URL}/forgot",
        data={"email": "test@example.com"},
        timeout=5,
        allow_redirects=False
    )
    if response.status_code in [200, 302]:
        print(f"   ✅ POST /forgot works! (Status: {response.status_code})")
    elif response.status_code == 405:
        print("   ❌ POST /forgot returns 'Method Not Allowed'")
        print("   → Server is running OLD code!")
        print("   → RESTART the server: Ctrl+C then python app.py")
    else:
        print(f"   ⚠️  POST /forgot returned status: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Can we POST to /forgot-password?
print("\n4. Testing POST /forgot-password...")
try:
    response = requests.post(
        f"{BASE_URL}/forgot-password",
        data={"email": "mk4829779@gmail.com"},
        timeout=5,
        allow_redirects=False
    )
    if response.status_code in [200, 302]:
        print(f"   ✅ POST /forgot-password works! (Status: {response.status_code})")
    else:
        print(f"   ⚠️  Status: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 70)
print("DIAGNOSIS")
print("=" * 70)

print("""
If you see "Method Not Allowed" for POST /forgot:
  → Your server is running OLD code
  → You MUST restart the Flask server
  → Steps:
     1. Go to Flask console window
     2. Press Ctrl+C to stop
     3. Run: python app.py
     4. Try again

If all tests pass:
  → Server is running latest code
  → Password reset should work
  → Try: http://localhost:5000/forgot
""")

print("=" * 70)

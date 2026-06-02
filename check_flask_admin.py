"""
Check what Flask is actually serving for /admin
"""
import requests

session = requests.Session()

print("="*60)
print("CHECKING FLASK ADMIN ROUTE")
print("="*60)

# Login first
print("\n1. Logging in...")
response = session.post("http://localhost:5000/admin-login", 
                       data={'admin_id': '8340', 'password': 'Manoj'},
                       allow_redirects=False)
print(f"   Status: {response.status_code}")

# Get admin page
print("\n2. Getting /admin page...")
response = session.get("http://localhost:5000/admin")
print(f"   Status: {response.status_code}")
print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
print(f"   Content-Length: {response.headers.get('Content-Length', 'N/A')}")
print(f"   Actual length: {len(response.text)} bytes")

if len(response.text) == 0:
    print("\n❌ RESPONSE IS EMPTY!")
    print("\nPossible causes:")
    print("1. Flask server not restarted after code changes")
    print("2. Exception in admin_panel() function")
    print("3. Template rendering error")
    print("\nCheck your Flask terminal for error messages!")
else:
    print(f"\n✅ Response has content ({len(response.text)} bytes)")
    print("\nFirst 200 characters:")
    print(response.text[:200])

print("\n" + "="*60)
print("CHECK YOUR FLASK TERMINAL NOW")
print("="*60)
print("Look for:")
print("- DEBUG: Fetched X users")
print("- DEBUG: Fetched X passes")
print("- Any error messages in red")
print("- 'GET /admin HTTP/1.1' 200 -")

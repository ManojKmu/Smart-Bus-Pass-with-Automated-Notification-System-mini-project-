"""
Quick script to check MySQL data
"""
from database import db

print("=" * 60)
print("MYSQL DATABASE CHECK")
print("=" * 60)

# Check connection
if db.connection and db.connection.is_connected():
    print("✅ MySQL Connected")
else:
    print("❌ MySQL Not Connected")
    exit()

# Get all users
print("\n" + "=" * 60)
print("USERS")
print("=" * 60)
users = db.get_all_users()
if users:
    for user in users:
        print(f"\nEmail: {user['email']}")
        print(f"Name: {user.get('name', 'N/A')}")
        print(f"Phone: {user.get('phone', 'N/A')}")
        print(f"City: {user.get('city', 'N/A')}")
        print(f"Address: {user.get('address', 'N/A')}")
        print(f"Created: {user.get('created_at', 'N/A')}")
else:
    print("No users found")

# Get login history
print("\n" + "=" * 60)
print("RECENT LOGINS (Last 10)")
print("=" * 60)
logins = db.get_login_history(limit=10)
if logins:
    for login in logins:
        print(f"{login['user_email']} - {login['login_time']}")
else:
    print("No login history found")

# Get all passes
print("\n" + "=" * 60)
print("ALL PASSES")
print("=" * 60)
query = "SELECT * FROM passes ORDER BY purchase_date DESC"
passes = db.fetch_all(query)
if passes:
    for pass_info in passes:
        print(f"\nUser: {pass_info['user_email']}")
        print(f"Type: {pass_info['pass_type']}")
        print(f"Price: ₹{pass_info['price']}")
        print(f"Route: {pass_info['route']}")
        print(f"Purchased: {pass_info['purchase_date']}")
        print(f"Expires: {pass_info['expiry_date']}")
        print(f"Status: {pass_info['status']}")
else:
    print("No passes found")

# Analytics
print("\n" + "=" * 60)
print("ANALYTICS")
print("=" * 60)
print(f"Total Users: {db.get_total_users()}")
print(f"Total Logins: {db.get_total_logins()}")
print(f"Total Passes: {db.get_total_passes()}")
print(f"Total Revenue: ₹{db.get_total_revenue():.2f}")
print(f"Users Today: {db.get_users_today()}")
print(f"Logins Today: {db.get_logins_today()}")
print(f"Active Users Today: {db.get_active_users_today()}")

print("\n" + "=" * 60)

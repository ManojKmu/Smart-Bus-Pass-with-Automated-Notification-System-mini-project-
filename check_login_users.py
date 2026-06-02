"""
Check which users have actually logged in
"""
from database import db

print("\n" + "="*60)
print("CHECKING LOGIN HISTORY")
print("="*60)

# Check login history
logins = db.fetch_all("SELECT DISTINCT user_email FROM login_history ORDER BY user_email")
print(f"\nUsers who have logged in ({len(logins)} unique users):")
for login in logins:
    print(f"  - {login['user_email']}")

# Check all users
all_users = db.fetch_all("SELECT email FROM users ORDER BY email")
print(f"\nAll registered users ({len(all_users)} total users):")
for user in all_users:
    print(f"  - {user['email']}")

# Test the INNER JOIN query
print(f"\n" + "="*60)
print("TESTING INNER JOIN QUERY")
print("="*60)

logged_in_users = db.fetch_all("""
    SELECT DISTINCT u.id, u.email, u.name, u.account_type, u.created_at 
    FROM users u
    INNER JOIN login_history lh ON u.email = lh.user_email
    ORDER BY u.created_at DESC
""")

print(f"\nUsers returned by INNER JOIN query ({len(logged_in_users)} users):")
for user in logged_in_users:
    print(f"  - {user['email']} | {user['name']} | {user['account_type']}")

print(f"\n" + "="*60)
if len(logged_in_users) < len(all_users):
    print("✅ QUERY IS WORKING - Filtering out users who haven't logged in")
    print(f"Showing {len(logged_in_users)} logged-in users instead of {len(all_users)} total users")
else:
    print("❌ QUERY NOT FILTERING - All users are being shown")
print("="*60)
"""
Check which users are real users (have passes) vs test accounts
"""
from database import db

print("\n" + "="*60)
print("CHECKING REAL USERS VS TEST ACCOUNTS")
print("="*60)

# Check users who have bought passes (real users)
users_with_passes = db.fetch_all("SELECT DISTINCT user_email FROM passes ORDER BY user_email")
print(f"\nUsers who have bought passes ({len(users_with_passes)} users):")
for user in users_with_passes:
    print(f"  ✅ {user['user_email']} (REAL USER)")

# Check all users
all_users = db.fetch_all("SELECT email FROM users ORDER BY email")
print(f"\nAll registered users ({len(all_users)} users):")
for user in all_users:
    has_pass = any(p['user_email'] == user['email'] for p in users_with_passes)
    status = "REAL USER" if has_pass else "TEST ACCOUNT"
    symbol = "✅" if has_pass else "❌"
    print(f"  {symbol} {user['email']} ({status})")

print(f"\n" + "="*60)
print("SOLUTION: Show only users who have bought passes")
print("="*60)

# Test query to show only users with passes
real_users = db.fetch_all("""
    SELECT DISTINCT u.id, u.email, u.name, u.account_type, u.created_at 
    FROM users u
    INNER JOIN passes p ON u.email = p.user_email
    ORDER BY u.created_at DESC
""")

print(f"\nUsers with passes query result ({len(real_users)} users):")
for user in real_users:
    print(f"  ✅ {user['email']} | {user['name']} | {user['account_type']}")

print(f"\nThis will show only REAL USERS who have actually used the website!")
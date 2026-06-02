"""
Check User Credentials in Database
"""
from database import db

print("=" * 60)
print("USER CREDENTIALS CHECK")
print("=" * 60)

# Get all users
users = db.get_all_users()

if users:
    print(f"\n✅ Found {len(users)} users in database:\n")
    
    for i, user in enumerate(users, 1):
        print(f"User {i}:")
        print(f"   Email: {user['email']}")
        print(f"   Name: {user['name']}")
        print(f"   Password: {user['password']}")
        print(f"   Account Type: {user['account_type']}")
        print(f"   Created: {user['created_at']}")
        print()
else:
    print("❌ No users found in database")

print("=" * 60)
print("CREDENTIAL VERIFICATION TEST")
print("=" * 60)

# Test credentials for known users
test_credentials = [
    {
        "email": "23c31a05a2.manoj@bitswgl.ac.in",
        "password": "Manoj123"
    },
    {
        "email": "lingammanojkumar178@gmail.com", 
        "password": "Kumar123"
    },
    {
        "email": "mk4829779@gmail.com",
        "password": "Manoj123"
    }
]

print("\nTesting credential verification:\n")

for i, cred in enumerate(test_credentials, 1):
    print(f"Test {i}: {cred['email']}")
    
    user = db.get_user(cred['email'])
    if user:
        if user['password'] == cred['password']:
            print(f"   ✅ VALID - Password matches")
            print(f"   Name: {user['name']}")
            print(f"   Account Type: {user['account_type']}")
        else:
            print(f"   ❌ INVALID - Password mismatch")
            print(f"   Expected: {cred['password']}")
            print(f"   Stored: {user['password']}")
    else:
        print(f"   ❌ USER NOT FOUND")
    print()

print("=" * 60)
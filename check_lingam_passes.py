"""Check passes for lingammanojkumar178@gmail.com"""
from database import Database

db = Database()
email = "lingammanojkumar178@gmail.com"

print(f"🔍 Checking passes for: {email}")
print("=" * 70)

passes = db.get_user_passes(email)

if passes:
    print(f"\n✅ Found {len(passes)} pass(es):\n")
    for i, p in enumerate(passes, 1):
        print(f"Pass #{i}:")
        print(f"   Type: {p.get('pass_type')}")
        print(f"   Price: ₹{p.get('price')}")
        print(f"   Route: {p.get('route')}")
        print(f"   Transaction: {p.get('transaction_id')}")
        print(f"   Purchase: {p.get('purchase_date')}")
        print(f"   Status: {p.get('status')}")
        print()
else:
    print(f"\n❌ NO PASSES FOUND!")
    print("\nThis means the 3 payments you made did NOT save to database.")
    print("\nREASON: Server was not restarted after fixes!")
    print("\nSOLUTION:")
    print("1. Stop the server (Ctrl+C)")
    print("2. Restart: python app_fast.py")
    print("3. Make a new payment")
    print("4. Check Flask console for: '✅ Pass saved to database'")

print("=" * 70)

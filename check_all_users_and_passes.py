"""Check all users and their passes in database"""
from database import Database

def check_all():
    """Check all users and passes"""
    print("🔍 CHECKING ALL USERS AND PASSES")
    print("=" * 70)
    
    db = Database()
    
    # Get all users
    print("\n📧 ALL USERS IN DATABASE:")
    print("-" * 70)
    
    users = db.get_all_users()
    if users:
        for user in users:
            email = user.get('email', 'N/A')
            name = user.get('name', 'N/A')
            account_type = user.get('account_type', 'N/A')
            
            print(f"\n   Email: {email}")
            print(f"   Name: {name}")
            print(f"   Type: {account_type}")
            
            # Check passes for this user
            passes = db.get_user_passes(email)
            if passes:
                print(f"   ✅ HAS {len(passes)} PASS(ES)")
                for i, p in enumerate(passes, 1):
                    print(f"      Pass #{i}: {p.get('pass_type')} - ₹{p.get('price')} - {p.get('route')}")
            else:
                print(f"   ⚠️  NO PASSES")
    else:
        print("   No users found")
    
    print("\n" + "=" * 70)
    print("\n💡 WHICH EMAIL DID YOU USE TO PURCHASE?")
    print("-" * 70)
    print("Look at the list above and tell me which email you used.")
    print("I'll add the pass to that account!")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    check_all()

"""Check existing passes in database for test users"""
from database import Database

def check_passes():
    """Check passes for test users"""
    print("🔍 Checking Existing Passes in Database")
    print("=" * 70)
    
    db = Database()
    
    # Test users
    test_users = [
        "mk4829779@gmail.com",
        "23c31a05a2.manoj@bitswgl.ac.in"
    ]
    
    for email in test_users:
        print(f"\n📧 User: {email}")
        print("-" * 70)
        
        try:
            passes = db.get_user_passes(email)
            
            if passes:
                print(f"   ✅ Found {len(passes)} pass(es)\n")
                
                for i, p in enumerate(passes, 1):
                    print(f"   Pass #{i}:")
                    print(f"      Type: {p.get('pass_type')}")
                    print(f"      Price: ₹{p.get('price')}")
                    print(f"      Route: {p.get('route')}")
                    print(f"      Distance: {p.get('distance')} km")
                    print(f"      Purchase: {p.get('purchase_date')}")
                    print(f"      Expiry: {p.get('expiry_date')}")
                    print(f"      Payment: {p.get('payment_method')}")
                    print(f"      Transaction: {p.get('transaction_id')}")
                    print(f"      Status: {p.get('status')}")
                    print()
            else:
                print(f"   ℹ️  No passes found for this user")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("=" * 70)
    print("✅ Check complete!")

if __name__ == "__main__":
    check_passes()

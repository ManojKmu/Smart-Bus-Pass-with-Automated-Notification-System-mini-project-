"""Add a pass to any email address"""
from database import Database
from datetime import datetime, timedelta
import sys

def add_pass_to_email(email):
    """Add a test pass to specified email"""
    print(f"🎫 Adding Pass to: {email}")
    print("=" * 70)
    
    db = Database()
    
    # Check if user exists
    user = db.get_user(email)
    if not user:
        print(f"❌ User {email} not found in database!")
        print("\nAvailable users:")
        users = db.get_all_users()
        for u in users:
            print(f"   - {u.get('email')}")
        return False
    
    print(f"✅ User found: {user.get('name')}")
    
    # Create pass
    expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    transaction_id = f"manual_{int(datetime.now().timestamp())}"
    
    print(f"\nCreating pass:")
    print(f"   Type: Monthly Pass")
    print(f"   Price: ₹500")
    print(f"   Route: Hyderabad → Warangal (150 km)")
    print(f"   Valid: 30 days")
    
    try:
        result = db.create_pass(
            user_email=email,
            pass_type="Monthly Pass",
            price=500.0,
            route="Hyderabad → Warangal (150 km)",
            distance=150.0,
            expiry_date=expiry,
            payment_method="Razorpay",
            transaction_id=transaction_id
        )
        
        if result:
            print(f"\n✅ Pass created successfully!")
            print(f"\n" + "=" * 70)
            print(f"\nNEXT STEPS:")
            print(f"1. Logout from website")
            print(f"2. Login with: {email}")
            print(f"3. Go to 'My Passes'")
            print(f"4. Your pass will appear!")
            print(f"\n" + "=" * 70)
            return True
        else:
            print(f"\n❌ Failed to create pass")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("ADD PASS TO ANY EMAIL")
    print("=" * 70)
    
    if len(sys.argv) > 1:
        email = sys.argv[1]
        add_pass_to_email(email)
    else:
        print("\nAvailable emails:")
        print("1. mk4829779@gmail.com")
        print("2. 23c31a05a2.manoj@bitswgl.ac.in")
        print("3. lingammanojkumar178@gmail.com")
        
        print("\nUsage:")
        print("python add_pass_to_any_email.py <email>")
        print("\nExample:")
        print("python add_pass_to_any_email.py lingammanojkumar178@gmail.com")

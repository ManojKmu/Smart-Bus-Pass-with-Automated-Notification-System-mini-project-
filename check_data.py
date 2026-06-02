"""
Check if there's actual data in the database
"""
import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='smartbus_db'
    )
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("CHECKING DATABASE DATA")
    print("="*60)
    
    # Check users
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"\n👥 Users: {user_count}")
    
    if user_count > 0:
        cursor.execute("SELECT email, name, account_type FROM users LIMIT 5")
        users = cursor.fetchall()
        print("Sample users:")
        for user in users:
            print(f"  - {user[0]} | {user[1]} | {user[2]}")
    
    # Check passes
    cursor.execute("SELECT COUNT(*) FROM passes")
    pass_count = cursor.fetchone()[0]
    print(f"\n🎫 Passes: {pass_count}")
    
    if pass_count > 0:
        cursor.execute("SELECT user_email, pass_type, price, status FROM passes LIMIT 5")
        passes = cursor.fetchall()
        print("Sample passes:")
        for p in passes:
            print(f"  - {p[0]} | {p[1]} | ₹{p[2]} | {p[3]}")
    
    # Check login history
    cursor.execute("SELECT COUNT(*) FROM login_history")
    login_count = cursor.fetchone()[0]
    print(f"\n🔐 Login History: {login_count}")
    
    if login_count > 0:
        cursor.execute("SELECT user_email, login_time FROM login_history ORDER BY login_time DESC LIMIT 5")
        logins = cursor.fetchall()
        print("Recent logins:")
        for l in logins:
            print(f"  - {l[0]} at {l[1]}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*60)
    if user_count == 0:
        print("⚠️ NO DATA FOUND!")
        print("Your database is empty. You need to:")
        print("1. Login with email (mk4829779@gmail.com / Manoj123)")
        print("2. Buy a pass")
        print("3. Then check admin panel again")
    else:
        print("✅ DATA EXISTS")
        print("Admin panel should show this data")
    print("="*60)
    
except Exception as e:
    print(f"❌ Error: {e}")

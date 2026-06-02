"""
Check actual database table structure
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
    print("CHECKING DATABASE TABLES")
    print("="*60)
    
    # Get all tables
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    print("\nTables in smartbus_db:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check each table structure
    for table in tables:
        table_name = table[0]
        print(f"\n{'='*60}")
        print(f"Table: {table_name}")
        print("="*60)
        
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        
        print("Columns:")
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*60)
    print("✅ CHECK COMPLETE")
    print("="*60)
    
except Exception as e:
    print(f"❌ Error: {e}")

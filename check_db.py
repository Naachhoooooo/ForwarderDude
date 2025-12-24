import sqlite3
import os
import sys

output_file = 'db_check_result.txt'

with open(output_file, 'w') as f:
    sys.stdout = f
    sys.stderr = f
    
    DB_PATH = 'forwarder_dude.db'
    print(f"Checking database at {os.path.abspath(DB_PATH)}")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("Running integrity_check...")
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        print(f"Integrity check result: {result}")
        
        print("Testing table creation...")
        cursor.execute("CREATE TABLE IF NOT EXISTS test_db_check (id INTEGER PRIMARY KEY)")
        conn.commit()
        print("Table created successfully.")
        
        cursor.execute("DROP TABLE test_db_check")
        conn.commit()
        print("Table dropped successfully.")
        
        conn.close()
        print("Database is healthy.")

    except Exception as e:
        print(f"Database check failed: {e}")

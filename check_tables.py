import sqlite3

conn = sqlite3.connect('../movielens_100k.db')

print('=== DATABASE TABLES ===')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

for table in tables:
    table_name = table[0]
    print(f'\nTable: {table_name}')
    
    # Get sample data
    try:
        sample = conn.execute(f"SELECT * FROM {table_name} LIMIT 1").fetchone()
        if sample:
            columns = [desc[0] for desc in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
            print(f'  Columns: {columns}')
        else:
            print('  No data')
    except Exception as e:
        print(f'  Error: {e}')

conn.close()

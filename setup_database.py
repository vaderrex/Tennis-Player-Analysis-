"""Create TennisRankings database on SQL Server."""

import pyodbc

# Connect to master database to create TennisRankings
connection_string = r'Driver={ODBC Driver 17 for SQL Server};Server=LAPTOP-Q6G1J5K1\SQLEXPRESS;Database=master;Trusted_Connection=yes;'

print('Connecting to SQL Server master database...')

try:
    # Connect with autocommit enabled
    conn = pyodbc.connect(connection_string, autocommit=True)
    cursor = conn.cursor()
    
    # Check if database exists
    cursor.execute("SELECT name FROM sys.databases WHERE name='TennisRankings'")
    if cursor.fetchone():
        print('✅ TennisRankings database already exists')
    else:
        print('Creating TennisRankings database...')
        cursor.execute('CREATE DATABASE TennisRankings')
        print('✅ TennisRankings database created successfully!')
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()

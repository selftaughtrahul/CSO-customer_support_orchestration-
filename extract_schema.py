import json
from core.db import get_db_connection

def extract_schema():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database in extract_schema.")
        return

    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SHOW TABLES")
    # depending on MySQL version, sometimes it returns a dict with 'Tables_in_<dbname>': 'table_name'
    tables = [list(row.values())[0] for row in cursor.fetchall()]
    
    simple_schema = {}
    
    print(f"Found {len(tables)} tables. Analyzing...")
    for table in tables:
        try:
            # Only include tables that have data
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()['count']
            
            if count > 0:
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                
                # Extract just the column names into a simple list
                column_names = [col['Field'] for col in columns]
                
                simple_schema[table] = column_names
                print(f"Added table: {table} ({len(column_names)} columns)")
        except Exception as e:
            print(f"Error analyzing table {table}: {e}")
            
    with open("database_schema.json", "w", encoding="utf-8") as f:
        json.dump(simple_schema, f, indent=4)
        
    print(f"Extracted simple schema for {len(simple_schema)} populated tables to database_schema.json")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    extract_schema()

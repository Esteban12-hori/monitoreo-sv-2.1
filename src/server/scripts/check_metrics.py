
import sqlite3
import json
from pathlib import Path

DB_PATH = Path("data/monitor.db")

def check():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get server id for test-server-processes
    cursor.execute("SELECT id FROM servers WHERE server_id = ?", ("test-server-processes",))
    row = cursor.fetchone()
    if not row:
        print("Server 'test-server-processes' not found")
        return
    
    server_id = row['id']
    print(f"Server ID: {server_id}")

    # Get latest metric
    cursor.execute("SELECT * FROM metrics WHERE server_id = ? ORDER BY ts DESC LIMIT 1", ("test-server-processes",))
    metric = cursor.fetchone()
    
    if not metric:
        print("No metrics found for this server")
        return

    # Check processes column
    try:
        processes_raw = metric['processes']
        print(f"Processes raw data: {processes_raw}")
        if processes_raw:
            processes = json.loads(processes_raw)
            print(f"Parsed processes count: {len(processes)}")
            print("First process:", processes[0] if processes else "None")
        else:
            print("Processes column is empty/null")
    except Exception as e:
        print(f"Error checking processes column: {e}")
        # Print all columns to see if 'processes' exists
        print("Columns:", metric.keys())

    conn.close()

if __name__ == "__main__":
    check()

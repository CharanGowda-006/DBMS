import sys
import mysql.connector

cfg = {l.split('=',1)[0].strip(): l.split('=',1)[1].strip() for l in open('.env') if '=' in l and not l.startswith('#')}
conn = mysql.connector.connect(host=cfg['DB_HOST'], user=cfg['DB_USER'], password=cfg['DB_PASSWORD'], database=cfg['DB_NAME'])
cur = conn.cursor(dictionary=True)

if len(sys.argv) > 1 and sys.argv[1].endswith('.sql'):
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        sql = f.read()
    # Execute commands separated by semicolon or multi-statement
    for stmt in sql.split(';'):
        stmt = stmt.strip()
        if stmt:
            try:
                cur.execute(stmt)
                while True:
                    if cur.description:
                        rows = cur.fetchall()
                        print(f"--- Results for: {stmt[:60]}... ({len(rows)} rows) ---")
                        for r in rows[:20]:
                            print(r)
                    if not cur.next() if hasattr(cur, 'next') else True:
                        break
            except Exception as e:
                print(f"Error on stmt: {stmt[:50]} -> {e}")
    conn.commit()
else:
    # Print researcher topics
    cur.execute("""
    SELECT r.r_id, r.r_name, GROUP_CONCAT(DISTINCT t.t_name ORDER BY t.t_name SEPARATOR ', ') AS topics,
           COUNT(DISTINCT t.t_id) as cnt
    FROM RESEARCHER r
    JOIN AUTHORS a ON r.r_id = a.r_id
    JOIN HAS_TOPIC ht ON a.p_id = ht.p_id
    JOIN TOPIC t ON ht.t_id = t.t_id
    GROUP BY r.r_id, r.r_name
    ORDER BY r.r_id
    """)
    for row in cur.fetchall():
        print(f"R{row['r_id']} ({row['r_name']}): [{row['topics']}] (cnt={row['cnt']})")

conn.close()


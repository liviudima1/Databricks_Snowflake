from databricks import sql
from config import DATABRICKS_CONFIG

conn = sql.connect(
    server_hostname=DATABRICKS_CONFIG["server_hostname"],
    http_path=DATABRICKS_CONFIG["http_path"],
    access_token=DATABRICKS_CONFIG["access_token"],
)

cursor = conn.cursor()

cursor.execute("""
    SELECT
        table_catalog,
        table_schema,
        table_name,
        last_altered,
        created
    FROM samples.information_schema.tables
    WHERE table_schema != 'information_schema'
    ORDER BY last_altered DESC
""")
rows = cursor.fetchall()
for row in rows:
    print(row)
cursor.close()

conn.close()
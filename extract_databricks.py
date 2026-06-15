import pandas as pd
from databricks import sql
from config import DATABRICKS_CONFIG

# --- Open the connection ---
conn = sql.connect(
    server_hostname=DATABRICKS_CONFIG["server_hostname"],
    http_path=DATABRICKS_CONFIG["http_path"],
    access_token=DATABRICKS_CONFIG["access_token"],
)

# --- Query 1: the table inventory (name + freshness) ---
inventory_query = """
    SELECT
        table_catalog || '.' || table_schema || '.' || table_name AS table_name,
        last_altered,
        created
    FROM samples.information_schema.tables
    WHERE table_schema != 'information_schema'
"""

# --- Query 2: the usage data (last accessed + access count) ---
usage_query = """
    SELECT
        source_table_full_name AS table_name,
        MAX(event_time) AS last_accessed,
        COUNT(*) AS access_count
    FROM system.access.table_lineage
    WHERE source_table_full_name IS NOT NULL
    GROUP BY source_table_full_name
"""

# --- Run both queries into DataFrames (must happen BEFORE the merge) ---
inventory_df = pd.read_sql(inventory_query, conn)
usage_df = pd.read_sql(usage_query, conn)

print("=== INVENTORY ===")
print(inventory_df.head(10))
print("Total tables:", len(inventory_df))

print("\n=== USAGE ===")
print(usage_df.head(10))
print("Total tables with usage records:", len(usage_df))

# --- Stage 3: NOW join them (both DataFrames now exist) ---
master_df = inventory_df.merge(
    usage_df,
    on="table_name",
    how="left"
)

print("\n=== MASTER (joined) ===")
print(master_df.head(15))
print("Total rows:", len(master_df))

# --- Stage 4: clean up the gaps so they're usable ---
# "never accessed" (NaN) should become a real signal, not a blank.

# fill missing access_count with 0 (never accessed = 0 accesses)
master_df["access_count"] = master_df["access_count"].fillna(0).astype(int)

# add a clear flag: was this table ever accessed?
master_df["ever_accessed"] = master_df["last_accessed"].notna()

print("\n=== MASTER (cleaned) ===")
print(master_df[["table_name", "access_count", "ever_accessed"]].head(15))
print("\nNever-accessed tables:", (~master_df["ever_accessed"]).sum())
print("Accessed tables:", master_df["ever_accessed"].sum())

conn.close()
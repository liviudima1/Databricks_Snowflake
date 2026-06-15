import pandas as pd
from databricks import sql
from config import DATABRICKS_CONFIG


def get_databricks_master():
    """Connect to Databricks, extract metadata, return a master DataFrame."""
    conn = sql.connect(
        server_hostname=DATABRICKS_CONFIG["server_hostname"],
        http_path=DATABRICKS_CONFIG["http_path"],
        access_token=DATABRICKS_CONFIG["access_token"],
    )

    inventory_query = """
        SELECT
            table_catalog || '.' || table_schema || '.' || table_name AS table_name,
            last_altered,
            created
        FROM samples.information_schema.tables
        WHERE table_schema != 'information_schema'
    """

    usage_query = """
        SELECT
            source_table_full_name AS table_name,
            MAX(event_time) AS last_accessed,
            COUNT(*) AS access_count
        FROM system.access.table_lineage
        WHERE source_table_full_name IS NOT NULL
        GROUP BY source_table_full_name
    """

    inventory_df = pd.read_sql(inventory_query, conn)
    usage_df = pd.read_sql(usage_query, conn)
    conn.close()

    # join + clean
    master_df = inventory_df.merge(usage_df, on="table_name", how="left")
    master_df["access_count"] = master_df["access_count"].fillna(0).astype(int)
    master_df["ever_accessed"] = master_df["last_accessed"].notna()
    master_df["platform"] = "Databricks"

    return master_df


# This lets you still run THIS file directly to test it
if __name__ == "__main__":
    df = get_databricks_master()
    print(df.head(10))
    print("Total rows:", len(df))
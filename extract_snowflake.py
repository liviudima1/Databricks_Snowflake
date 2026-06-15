import pandas as pd
import snowflake.connector
from config import SNOWFLAKE_CONFIG


def get_snowflake_master():
    """Connect to Snowflake, extract metadata, return a master DataFrame."""
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)

    inventory_query = """
        SELECT
            table_catalog || '.' || table_schema || '.' || table_name AS table_name,
            last_altered,
            created
        FROM SNOWFLAKE_SAMPLE_DATA.INFORMATION_SCHEMA.TABLES
        WHERE table_schema != 'INFORMATION_SCHEMA'
    """

    usage_query = """
        SELECT
            objects.value:objectName::string AS table_name,
            MAX(query_start_time) AS last_accessed,
            COUNT(*) AS access_count
        FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY,
             LATERAL FLATTEN(input => base_objects_accessed) AS objects
        WHERE query_start_time >= DATEADD(DAY, -30, CURRENT_TIMESTAMP())
        GROUP BY objects.value:objectName::string
    """

    inventory_df = pd.read_sql(inventory_query, conn)
    usage_df = pd.read_sql(usage_query, conn)
    conn.close()

    # join + clean
    master_df = inventory_df.merge(usage_df, on="TABLE_NAME", how="left")
    master_df["ACCESS_COUNT"] = master_df["ACCESS_COUNT"].fillna(0).astype(int)
    master_df["EVER_ACCESSED"] = master_df["LAST_ACCESSED"].notna()
    master_df["PLATFORM"] = "Snowflake"

    # --- standardize column names to lowercase to MATCH Databricks ---
    master_df.columns = [c.lower() for c in master_df.columns]

    return master_df


if __name__ == "__main__":
    df = get_snowflake_master()
    print(df.head(10))
    print("Total rows:", len(df))
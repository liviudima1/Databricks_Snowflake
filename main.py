import pandas as pd
from extract_databricks import get_databricks_master
from extract_snowflake import get_snowflake_master

print("Extracting from Databricks...")
databricks_df = get_databricks_master()

print("Extracting from Snowflake...")
snowflake_df = get_snowflake_master()

combined_df = pd.concat([databricks_df, snowflake_df], ignore_index=True)

print("Databricks tables:", len(databricks_df))
print("Snowflake tables:", len(snowflake_df))
print("Combined total:", len(combined_df))

print("\nBreakdown by platform:")
print(combined_df["platform"].value_counts())

print("\nSample rows:")
print(combined_df[["table_name", "platform", "ever_accessed", "access_count"]].head(5))
print("...")
print(combined_df[["table_name", "platform", "ever_accessed", "access_count"]].tail(5))

import datetime

now = pd.Timestamp.now(tz="UTC")

combined_df["days_since_altered"] = (now - combined_df["last_altered"]).dt.days

def score_row(row):
    score = 0
    # staleness: up to 60 points, maxing out around 1 year idle
    score += min(row["days_since_altered"] / 365 * 60, 60)
    # never accessed: +40 (strong minimize signal)
    if not row["ever_accessed"]:
        score += 40
    return round(score, 1)

combined_df["minimaize_score"] = combined_df.apply(score_row, axis=1)

def categorize(s):
    if s >= 75: return "Minimize"
    if s >= 50: return "Review"
    if s >= 25: return "Monitor"
    return "Healthy"

combined_df["action"] = combined_df["minimaize_score"].apply(categorize)

ranked = combined_df.sort_values("minimaize_score", ascending=False)
print("\n=== TOP MINIMIZE CANDIDATES (across both platforms) ===")
print(ranked[["table_name", "platform", "days_since_altered",
              "ever_accessed", "minimaize_score", "action"]].head(15).to_string(index=False))

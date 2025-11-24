from arcgis.gis import GIS
from arcgis.features import FeatureLayer
import pandas as pd

# 1. Connect to ArcGIS Online

gis = GIS("https://www.arcgis.com", "your_username", "your_password")

# 2. Access hosted feature layer by item ID + layer index

item_id = "YOUR_FEATURE_LAYER_ITEM_ID"
fl_item = gis.content.get(item_id)

# If the item contains multiple layers, pick the correct one:
layer = fl_item.layers[0]  # adjust index if needed
print(f"Connected to layer: {layer.properties.name}")

# 3. Query all records

features = layer.query(where="1=1", out_fields="*", return_geometry=False)
df = features.sdf  # Spatially-enabled dataframe (pandas-like)

print(f"Loaded {len(df)} records.\n")

# 4. Define QA checks

qa_report = {}

# Example required fields
required_fields = ["SiteID", "Status", "CreatedDate"]

# ---- Null value check ----
null_issues = {}
for field in required_fields:
    null_rows = df[df[field].isna()]
    if len(null_rows) > 0:
        null_issues[field] = len(null_rows)

qa_report["null_checks"] = null_issues

# ---- Duplicate ID check ----
if "SiteID" in df.columns:
    duplicates = df[df.duplicated("SiteID", keep=False)]
    qa_report["duplicate_ids"] = len(duplicates)
else:
    qa_report["duplicate_ids"] = "Field not present"

# ---- Coded domain validation (example) ----
valid_status_values = ["Active", "Inactive", "Proposed"]
if "Status" in df.columns:
    bad_status = df[~df["Status"].isin(valid_status_values)]
    qa_report["bad_status_values"] = len(bad_status)

# ---- Range check example ----
if "Score" in df.columns:
    out_of_range = df[(df["Score"] < 0) | (df["Score"] > 100)]
    qa_report["score_range_issues"] = len(out_of_range)

# ---- Date validity example ----
if "CreatedDate" in df.columns:
    weird_dates = df[df["CreatedDate"] > pd.Timestamp.now()]
    qa_report["future_dates"] = len(weird_dates)

# 5. Output QA Report

print("\n====== QA REPORT ======\n")
for check, result in qa_report.items():
    print(f"{check}: {result}")

# Export failures to CSV for review
duplicates.to_csv("duplicate_ids.csv", index=False)
print("\nExported duplicate ID list to duplicate_ids.csv")
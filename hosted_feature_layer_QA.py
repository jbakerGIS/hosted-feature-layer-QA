from arcgis.gis import GIS
import pandas as pd
from datetime import date

# Set input parameters
ITEM_ID = "b7fd31c8206f4fdb9b66fcced3271e28"
OUTPUT_PATH = r"C:/Users/viver/Documents/scripts/scrap"

# Connect to AGOL
gis = GIS("https://www.arcgis.com", "Baker.jst", "Dr3amb!g")

# Access hosted feature layer by item ID
fl_item = gis.content.get(ITEM_ID)

# Get the layer name
layer = fl_item.layers[0]  # adjust index if needed
layer_name = layer.properties.name

print(f'Connected to layer: {layer_name}')

# Prompt user to confirm layer name before proceeding
while True:
    choice = input("Is this the correct layer name? (y/n): ").lower()
    if choice == 'y':
        print("Continuing the QA check...")
        # Your code to continue the process
        break  # Exit the loop
    elif choice == 'n':
        print("Exiting the QA check. Please verify the correct layer item ID and try again.")
        break  # Exit the loop
    else:
        print("Invalid input. Please enter 'y' or 'n'.")

# Query all records
feature = layer.query(where="1=1", out_fields="*", return_geometry=False)

# Convert to SEDF
sdf = feature.sdf

# Show how many records exist in the layer
print(f"Layer consists of {len(sdf)} records.\n")

# Create empty lists for functions
field_list = []
qa_results = []

# Return fields from the hosted feature layer  
print(f"Fields in layer '{layer.properties.name}':")
for field in layer.properties.fields:
    field_list.append(field['name'])
    print(f"  Name: {field['name']}, Type: {field['type']}\n")

# Helper function to add a QA issue to the output list
def add_issue(issue_type, field, oid, value=None, notes=None):
    qa_results.append({
        "IssueType": issue_type,
        "FieldName": field,
        "ObjectID": oid,
        "Value": value,
        "Notes": notes
    })

# ==================== MAIN LOGIC ====================

def null_check(df, fields):
    '''Check for null values in the feature layer table.'''

    print("Checking for NULL values...\n")

    for field in fields:
        null_rows = df[df[field].isna()]
        
        if len(null_rows) > 0:
            print(f"- Null values in '{field}':")
            for _, row in null_rows.iterrows():
                oid = row['OBJECTID']
                print(f"      ObjectID: {oid}")
                add_issue("NULL Value", field, oid, value=None)
        else:
            print(f"No null values in '{field}'")

def duplicate_check(df, fields):
    '''Check for duplicate values in the feature layer table.'''

    print("\nChecking for duplicate values...\n")

    for field in fields:
        # Remove unnecessary fields from duplicate check
        if field not in ['City', 'State','Zip_Code', 'Last_Updated', 'QA_Status']:
            duplicates = df[df[field].duplicated(keep=False) & df[field].notna()]

            # If duplicates found, log them
            if len(duplicates) > 0:
                print(f"- Duplicates found in '{field}':")
                for val in duplicates[field].unique():
                    group = duplicates[duplicates[field] == val]
                    oids = group['OBJECTID'].tolist()
                    print(f"    Value: '{val}' → ObjectIDs {oids}")

                    # Add each duplicate occurrence to results
                    for oid in oids:
                        add_issue("Duplicate Value", field, oid, value=val, 
                                notes=f"Duplicate of value '{val}'")
            else:
                print(f"No duplicates in '{field}'")

def domain_check(df, fl):
    '''Check for invalid coded values in domain fields.'''

    print("\nChecking domain/coded-value fields...\n")
    
    # Identify fields with domains
    domain_fields = [f["name"] for f in fl.properties.fields 
                     if "domain" in f and f["domain"]]
    
    # Create a map of field names to their valid coded values
    domain_map = {}
    for f in fl.properties.fields:
        if f["name"] in domain_fields and "domain" in f and f["domain"]:
            domain_map[f["name"]] = [d["code"] for d in f["domain"]["codedValues"]]

    # Check each domain field for invalid values
    for field, valid_codes in domain_map.items():
        invalid_rows = df[~df[field].isin(valid_codes) & df[field].notna()]
        
        # If invalid values found, log them
        if len(invalid_rows) > 0:
            print(f"  - Invalid coded values in '{field}':")
            for _, row in invalid_rows.iterrows():
                oid = row['OBJECTID']
                bad_val = row[field]
                print(f"      ObjectID: {oid} → '{bad_val}'")
                add_issue("Invalid Domain Value", field, oid, 
                        value=bad_val, 
                        notes=f"Not in valid domain list: {valid_codes}")
        else:
            print(f"All domain values valid in '{field}'")

def geometry_check(df):
    '''Check for missing geometries in the feature layer table.'''

    print("Checking for empty or missing geometry...\n")

    # Query all features with geometry
    feature_set = layer.query(where="1=1", return_geometry=True)
    features = feature_set.features
    
    # Check each feature for missing geometry
    invalid_geometries = []
    for f in features:
        geometry = f.geometry
        if not geometry:
            oid = f.attributes['OBJECTID']
            invalid_geometries.append(oid)
            add_issue("Missing Geometry", "SHAPE", oid, notes="Null geometry")

    # If missing geometries, print the OIDs
    if invalid_geometries:
        print("  - Missing geometry:")
    for obj_id in invalid_geometries:
        print(f"      ObjectID: {obj_id}")
            
    else:
       print("All features have valid geometry")

def create_qa_report(results):
    '''Create a QA report DataFrame from the results list and export it as a csv file.'''

    print("\nWriting QA report to CSV...\n")

    # Create DataFrame from QA results
    qa_df = pd.DataFrame(results)

    # Export QA results if any issues found
    if len(qa_df) == 0:
        print("No issues found. No CSV created.")
    else:
        # Get today's date for file naming
        export_date = date.today()
        # Save QA results to CSV
        file_name = f'{layer_name}_QA_{export_date}.csv'
        export_path = OUTPUT_PATH + "/ "+ file_name
        qa_df.to_csv(export_path, index=False)
        print(f"QA report successfully saved to: {OUTPUT_PATH}/{file_name}")

    print("\nQA Complete.")

def main():
    '''Main function to run the script's logic'''

    # QA Checks
    null_check(sdf, field_list)
    duplicate_check(sdf, field_list)
    domain_check(sdf, layer)
    geometry_check(sdf)
    
    # Create QA report
    create_qa_report(qa_results)

# Ensure code runs only when executed directly
if __name__ == "__main__":
    main()
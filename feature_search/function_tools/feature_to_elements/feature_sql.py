# GET SQL STRUCTURE BY FIELD
import json
import re

#Load SQL field indexing
with open("feature_search/SQL_parser/field_sql_index.json", "r", encoding="utf-8") as file:
    field_sql_index = json.load(file)

# SQL RECONSTRUCTION
def normalize_field_name(field_name):
    return " ".join(field_name.lower().replace("_", " ").split())

def get_feature_sql(value: str):
    value = value.lower().strip()


    # Split multiple fields
    fields = re.split( r"\s*(?:,|\bor\b|\band\b)\s*",value )
    fields = [ field.strip() for field in fields if field.strip()]


    results = {}
    not_found = []

    # Process fields

    for field_name in fields:

        normalized_field = normalize_field_name(field_name)

        # Search SQL index
        entries = field_sql_index.get(normalized_field, [])


        if not entries:
            not_found.append(field_name)
            continue


        field_results = []


        # Return ONLY structure
        for entry in entries:
            structure = (entry.get("sql", {}).get("structure", {}))


            field_results.append({
                "field": field_name,
                "yaml_file": entry.get("yaml_file",""),
                "entity": entry.get("entity",""),
                "feature": entry.get("feature",""),
                "structure": structure
            })

        results[field_name] = field_results

    return {
        "results": results,
        "not_found": not_found
    }

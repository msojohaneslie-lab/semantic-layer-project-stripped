import re
import json
import yaml
from pathlib import Path

#Load indexing
with open("feature_search/index_dictionary/feature_index.json", "r", encoding="utf-8") as file:
    feature_index = json.load(file)

BASE_DIR = Path(__file__).parents[2]
YAML_FOLDER = BASE_DIR / "yaml_list"

def get_feature_field_info(value: str, info: str):
    value = value.lower().strip()
    info = info.lower().strip()

    fields = re.split(
        r"\s*(?:,|\bor\b|\band\b)\s*",
        value
    )

    fields = [field.strip() for field in fields if field.strip()]
    results = {}
    not_found = []
    
    #Process all fields
    for field_name in fields: 

        files = feature_index["field_exact"].get(field_name, [])

        if not files:
            files = feature_index["field_seperated"].get(field_name,[])

        field_results = []

        #If field does not exist
        if not files:
            not_found.append(field_name)
            continue

        #Open necessary YAML
        filename = files[0]
        yaml_path = YAML_FOLDER / filename

        with open(yaml_path,"r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

           
        #Get the feature_fields
        for field in data.get("feature_fields", []):

            if field.get("name", "").lower() != field_name:
                continue

            result = {
                "field": field.get("name", "")
            }

                
            #Get requested info
            if info == "description":
                result["description"] = field.get("description","")

            elif info == "business_logic":
                result["business_logic"] = field.get("business_logic", "")

            elif info == "type":
                result["type"] = field.get("type","")

            elif info == "all":
                result["type"] = field.get("type", "")
                result["description"] = field.get("description", "")
                result["business_logic"] = field.get("business_logic","")

            else:
                result["error"] = (f"Unknown information type '{info}'.")

            field_results.append(result)

        results[field_name] = field_results

    return {
        "results": results,
        "info" : info,
        "not_found" : not_found
        }
#Users know the features name
import re
import json
import yaml
from pathlib import Path

#Load indexing
with open("feature_search/index_dictionary/feature_index.json", "r", encoding="utf-8") as file:
    feature_index = json.load(file)

BASE_DIR = Path(__file__).parents[2]
YAML_FOLDER = BASE_DIR / "yaml_list"

def get_feature_view_info(value: str, info: str):
    value = value.lower().strip()
    info = info.lower().strip()

   
    #Split features
    features = re.split(
        r"\s*(?:,|\bor\b|\band\b)\s*",
        value
    )

    features = [ feature.strip()  for feature in features if feature.strip()]

    results = {}
    not_found = []

    for feature in features:
        files = feature_index["name_exact"].get(feature, []) 

        if not files:
            files = feature_index["name_seperated"].get( feature,[] )

        if not files:
            not_found.append(feature)
            continue

        #Get top file
        filename = files[0]

        yaml_path = YAML_FOLDER / filename

        with open( yaml_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

       
        #Get requested information
        # if info == "name":

        #     results[feature] = data.get(
        #         "name",
        #         ""
        #     )

        if info == "description":
            results[feature] = data.get("description", "")

        elif info == "entity":
            results[feature] = data.get("entity","")

        elif info == "ttl":
            results[feature] = data.get("ttl","")

        elif info == "feature_fields":
            results[feature] = [field.get("name", "") for field in data.get("feature_fields", [])]

        else:
            results[feature] = (f"Unknown information type '{info}'.")

    return {"results": results,"info" : info,"not_found" : not_found}
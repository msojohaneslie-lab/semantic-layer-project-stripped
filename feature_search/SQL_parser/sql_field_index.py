import json
import yaml
from pathlib import Path
from sql_parsing_test import (parse_sql,trace_field)


BASE_DIR = Path(__file__).resolve().parent

YAML_FOLDER = Path(
    r"C:\Users\5003186\Documents\Intern\Project\feature-search\feature_search\yaml_list"
)

INDEX_FILE = BASE_DIR / "field_sql_index.json"


# NORMALIZE FIELD NAME
def normalize_field_name(field_name):
 
    return " ".join(field_name.lower().replace("_", " ").split())


# BUILD INDEX
def build_field_index():

    index = {}
    yaml_files = list( YAML_FOLDER.glob("*.yaml"))

    print(f"Found {len(yaml_files)} YAML files")

    # LOOP YAML FILES
    for yaml_file in yaml_files:

        print(f"\nProcessing: {yaml_file.name}")

        # READ YAML
        try:
            with open(yaml_file,"r",encoding="utf-8") as f:
                data = yaml.safe_load(f)

        except Exception as e:
            print(f"  ERROR reading YAML: {e}")
            continue


        # GET FEATURE INFORMATION
        feature_name = data.get("name")
        entity = data.get("entity")
        sql = data.get("sql")
        fields = data.get("feature_fields",[])


        # VALIDATION
        if not feature_name:
            print("No feature_name")
            continue

        if not sql:
            print("No SQL")
            continue

        if not fields:
            print("No fields")
            continue


        # PARSE SQL ONCE
        try:
            tree = parse_sql(sql)

        except Exception as e:
            continue


        # LOOP FIELDS
        for field in fields:

            # GET FIELD NAME
            if isinstance(field, dict):
                field_name = field.get("name")

            else:
                field_name = field

            if not field_name:
                continue


            print(f"  Field: {field_name}")


            # TRACE FIELD
            try:
                result = trace_field(tree,field_name)

            except Exception as e:
                print(f"ERROR tracing: {e}")

                result = {
                    "field": field_name,
                    "lineage": [],
                    "structure": {},
                    "error": str(e)
                }


            # CREATE FIELD ENTRY

            field_entry = {

                "yaml_file":
                    yaml_file.name,

                "entity":
                    entity,

                "feature":
                    feature_name,

                "sql": {

                    "lineage":
                        result.get(
                            "lineage",
                            []
                        ),

                    "structure":
                        result.get(
                            "structure",
                            {}
                        )
                }
            }


            # NORMALIZE FIELD NAME FOR INDEX
            normalized_field_name = normalize_field_name(field_name)

            # ADD TO INDEX
            if normalized_field_name not in index:

                index[normalized_field_name] = []


            index[normalized_field_name].append(
                field_entry
            )


    # SAVE INDEX
    with open(INDEX_FILE,"w",encoding="utf-8") as f:
        json.dump(
            index,
            f,
            indent=2,
            ensure_ascii=False
        )


    print(f"Fields indexed: {len(index)}")



if __name__ == "__main__":
    build_field_index()


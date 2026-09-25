from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parents[3]
YAML_FOLDER = BASE_DIR / "yaml_list"


def add_feature_field(yaml_file: str, field_name: str, field_type: str, description: str, business_logic: str, sql: str, entity:str):
    yaml_path = YAML_FOLDER / yaml_file

    # 1. Read existing YAML
    with open(yaml_path,"r",encoding="utf-8") as file:
        data = yaml.safe_load(file)

    # 2. Validate entity
    yaml_entity = data.get("entity")
    if yaml_entity.strip().lower() != entity.strip().lower():
        return {
            "status": "error",
            "message": (
                f"Entity mismatch. "
                f"Feature field '{field_name}' belongs to entity "
                f"'{entity}', but YAML file '{yaml_file}' "
                f"belongs to entity '{yaml_entity}'."
            ),
            "feature_entity": entity,
            "yaml_entity": yaml_entity,
            "yaml_file": yaml_file,
        }


    # 2. Create new feature field
    new_feature_field = {
        "name": field_name,
        "type": field_type,
        "description": description,
        "business_logic": business_logic,
    }

    #If it exists already, return error
    for feature in data["feature_fields"]:
        if feature.get("name") == field_name:
            return {
                "status": "error",
                "message": (
                    f"Feature field '{field_name}' "
                    "already exists in this feature view."
                ),
            }
    # 3. Add it
    data["feature_fields"].append(new_feature_field)

    # 4. Write YAML
    with open(yaml_path,"w", encoding="utf-8") as file:
        yaml.safe_dump(data, file, sort_keys=False, allow_unicode=True)

    return {
        "status": "success",
        "message": (
            f"Feature '{field_name}' "
            f"added to '{yaml_file}'."
        ),
        "sql": sql,
        "yaml_file": yaml_file
    }

import yaml
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parents[3]
YAML_FOLDER = BASE_DIR / "yaml_list"

def create_feature_view_yaml(
    source_type: str,
    name: str,
    description: str,
    entity: str,
    field_name: str,
    field_type: str,
    field_description: str,
    business_logic: str,
    sql: str,
    domain: str,
    confidentiality: Optional[str]
):
   

    # 1. VALIDATE REQUIRED PARAMETERS
    required_parameters = {
        "source_type": source_type,
        "name": name,
        "description": description,
        "entity": entity,
        "field_name": field_name,
        "field_type": field_type,
        "field_description": field_description,
        "business_logic": business_logic,
        "sql": sql,
        "domain": domain
    }

    missing_parameters = [
        key
        for key, value in required_parameters.items()
        if value is None
        or not isinstance(value, str)
        or not value.strip()
    ]

    if missing_parameters:
        return {
            "status": "missing_parameters",
            "missing_parameters": missing_parameters,
            "message": (
                "The following parameters are missing: "
                + ", ".join(missing_parameters)
            ),
        }

    file_name = f"{name}.yaml"
    yaml_file = YAML_FOLDER / file_name

    if yaml_file.exists():
        return {
            "status": "file_exists",
            "file": file_name,
            "message": (
                f"The feature view YAML "
                f"'{file_name}' already exists."
            ),
        }
    
    # 2. NORMALIZE VALUES
    source_type = source_type.strip()
    name = name.strip()
    description = description.strip()
    entity = entity.strip()
    field_name = field_name.strip()
    field_type = field_type.strip()
    field_description = field_description.strip()
    business_logic = business_logic.strip()
    sql = sql.strip()


    # 4. CREATE YAML STRUCTURE
    yaml_data = {
        "source_type": source_type,
        "name": name,
        "description": description,
        "entity": entity,
        "feature_fields": [
            {
                "name": field_name,
                "type": field_type,
                "description": field_description,
                "business_logic": business_logic,
            }
        ],

        "tags": [
            {
                "domain": domain,
                "confidentiality": confidentiality
            }
        ],

        "sql": sql,
    }

    # 5. MAKE SURE YAML DIRECTORY EXISTS
    YAML_FOLDER.mkdir(parents=True, exist_ok=True,)

    # 6. CREATE FILE NAME
    file_name = f"{name}.yaml"
    yaml_file = YAML_FOLDER / file_name

    # 7. PREVENT ACCIDENTAL OVERWRITE
    if yaml_file.exists():

        return {
            "status": "file_exists",
            "file": file_name,
            "message": (
                f"The feature view YAML "
                f"'{file_name}' already exists."
            ),
        }

    # 8. WRITE YAML
    try:
        with open(yaml_file,"w",encoding="utf-8",) as f:
            yaml.safe_dump(yaml_data,f,sort_keys=False,allow_unicode=True, default_flow_style=False,)

    except Exception as e:
        return {
            "status": "error",
            "message": (
                f"Failed to create YAML file: {str(e)}"
            ),
        }

    # 9. RETURN RESULT
    return {
        "status": "created",
        "file": file_name,
        "path": str(yaml_file),
        "feature_view": name,
        "entity": entity,
        "field": field_name,
        "message": (
            f"Feature view '{name}' was created "
            f"successfully."
        ),
    }

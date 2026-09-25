from typing import Optional

def is_missing(value):
    if value is None:
        return True

    if not isinstance(value, str):
        return True

    value = value.strip()

    if not value:
        return True

    if value.lower() in {"null", "none"}:
        return True

    return False

def validate_parameters(
    field_name: Optional[str] = None,
    field_type: Optional[str] = None,
    description: Optional[str] = None,
    business_logic: Optional[str] = None,
    entity: Optional[str] = None,
    sql: Optional[str] = None,
):

    # 1. VALIDATE REQUIRED PARAMETERS
    required_parameters = {
        "field_name": field_name,
        "field_type": field_type,
        "description": description,
        "business_logic": business_logic,
        "entity": entity,
        "sql": sql,
    }

    missing_parameters = []

    for key, value in required_parameters.items():

        if is_missing(value):
            missing_parameters.append(key)

        if missing_parameters:

            return {
                "status": "missing_parameters",

                "missing_parameters": missing_parameters,

                "message": (
                    "The following parameters are missing: "
                    + ", ".join(missing_parameters)
                ),
            }

    # 2. VALIDATE AND NORMALIZE FIELD TYPE

    field_type_mapping = {
        "int": "INTEGER",
        "integer": "INTEGER",
        "Integer": "INTEGER",
        "INT" : "INTEGER",

        "double": "DOUBLE",
        "float": "DOUBLE",
        "Double": "DOUBLE",
        "Float" : "DOUBLE",
        "FLOAT" : "DOUBLE",

        "string": "STRING",
        "str": "STRING",
        "char" : "STRING",
        "CHAR" : "STRING",

        "boolean": "BOOLEAN",
        "bool": "BOOLEAN",

        "timestamp": "TIMESTAMP",
        "datetime": "TIMESTAMP",
    }

    normalized_field_type = field_type.strip().lower()

    if normalized_field_type not in field_type_mapping:

        return {
            "status": "invalid_field_type",
            "field_type": field_type,
            "allowed_types": [
                "INTEGER",
                "DOUBLE",
                "STRING",
                "BOOLEAN",
                "TIMESTAMP",
            ],
            "message": (
                f"Invalid field type '{field_type}'. "
                "Please use INT, DOUBLE, STRING, BOOLEAN, "
                "or TIMESTAMP."
            ),
        }

    normalized_field_type = field_type_mapping[
        normalized_field_type
    ]

    # 3. RETURN NORMALIZED INPUT
    return {
        "status": "valid",
        "field_name": field_name.strip(),
        "field_type": normalized_field_type,
        "description": description.strip(),
        "business_logic": business_logic.strip(),
        "entity": entity.strip(),
        "sql": sql.strip(),
    }
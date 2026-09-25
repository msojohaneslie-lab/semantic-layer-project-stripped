from ...global_function.read_json import load_json_file
from pathlib import Path
from typing import Optional 

BASE_DIR = Path(__file__).resolve().parents[3]
FIELD_INDEX_FILE = BASE_DIR /"index_dictionary"/"field_index.json"


def check_exact_field_duplicate(field_name: str, entity: str,):
    field_index = load_json_file(FIELD_INDEX_FILE)

    existing_fields = field_index.get(field_name,[])

    exact_matches = []
    for existing in existing_fields:
        existing_entity = (existing.get("entity", "").strip().lower())

        if existing_entity == entity:
            exact_matches.append(existing)

    return exact_matches

def validate_exact_feature_duplicate(field_name: str,field_type: str,description: str,business_logic: str,entity: str,sql: str, flag: Optional[bool]):
    if flag is True:
        matches = check_exact_field_duplicate(field_name=field_name, entity=entity.strip().lower())
    
        if matches:
            return {
                "status": "duplicate_warning",
                "match_type": "exact",
                "field": field_name,
                "entity": entity,
                "existing_features": [
                    {
                        "feature": item.get("feature"),
                        "entity": item.get("entity"),
                        "type": item.get("type"),
                        "file": item.get("file")
                    }
                    for item in matches
                ],
                "requires_confirmation": True,
                "message": (
                    f"A field named '{field_name}' "
                    f"already exists for entity '{entity}'."
                )
            }
    
    return {
        "status": "valid",
        "message": "No exact duplicate found.",
        "field_name": field_name,
        "field_type": field_type,
        "description": description,
        "business_logic": business_logic,
        "entity": entity,
        "sql": sql,
    }
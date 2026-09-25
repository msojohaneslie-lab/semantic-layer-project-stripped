import json
from ...global_function.read_json import load_json_file
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[3]
ENTITY_INDEX_FILE = BASE_DIR / "index_dictionary"/"entities_index.json"

def get_entity_feature_views(entity: str):
    entity_index = load_json_file(ENTITY_INDEX_FILE)

    exact_name_index = entity_index.get("name_exact",{})
    separated_name_index = entity_index.get("name_seperated",{})

    exact_files = exact_name_index.get(entity,[])
    separated_files = separated_name_index.get(entity,[])

    # Combine both indexes and remove duplicates.
    entity_files = list(
        set(
            exact_files
            + separated_files
        )
    )

    return entity_files


def validate_entities(field_name: str,field_type: str,description: str,business_logic: str,entity: str,sql: str):

    entity = entity.strip().lower()

    try:
        entity_files = get_entity_feature_views(entity)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to read entities index: {e}"
        }

    if not entity_files:

        entity_index = load_json_file(ENTITY_INDEX_FILE)

        exact_name_index = entity_index.get("name_exact", {})
        separated_name_index = entity_index.get("name_seperated", {})

        entity_exists = (
            entity in exact_name_index
            or entity in separated_name_index
        )

        if not entity_exists:
            return {
                "status": "invalid_entity",
                "entity": entity,
                "message": f"Entity '{entity}' does not exist."
            }

    return {
        "status": "valid",
        "entity": entity,
        "feature_views": entity_files,
        "field_name": field_name,
        "field_type": field_type,
        "description": description,
        "business_logic": business_logic,
        "entity": entity,
        "sql": sql,
    }
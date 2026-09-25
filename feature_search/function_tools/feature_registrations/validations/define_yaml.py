from ...feature_registrations.validations.validate_entity import get_entity_feature_views

def choose_yaml(field_name: str,field_type: str,description: str,business_logic: str,entity: str,sql: str, similar_feature_view: list[str]):
    try:
        entity_files = get_entity_feature_views(entity)

    except Exception as e:
        return {
            "status": "error",
            "message": (
                "Failed to read entities index: "
                f"{str(e)}"
            ),
        }

    if len(entity_files) == 0:
        if len(entity_files) == 0:
            return {
                "status": "feature_view_required",
                "requires_user_input": True,
                "field": field_name,
                "type": field_type,
                "entity": entity,
                "description": description,
                "business_logic": business_logic,
                "sql": sql,
                "existing_feature_views": [],
                "required_parameters": [
                    "source_type",
                    "name",
                    "description",
                    "tags",
                ],
        
                "message": (
                    f"Field '{field_name}' passed "
                    "exact and semantic duplicate "
                    "validation, but entity "
                    f"'{entity}' does not have an "
                    "existing feature view. "
                    "Ask the user for source_type, "
                    "feature-view name, description, "
                    "and tags."
                    ),
                }
    else:
        return {
            "feature_views_recommendation" : similar_feature_view,
            "message": (
                "Ask the users whether to choose the YAML file from feature_view_recommendation"
                "or users want to define which YAML to update"
                "or users prefer to make new YAML file"
            ),
            "field": field_name,
            "type": field_type,
            "entity": entity,
            "description": description,
            "business_logic": business_logic,
            "sql": sql,
        }
        
        
import re
import yaml
import json
from pathlib import Path

BASE_DIR = Path(__file__).parents[2]
ENTITY_YAML_FOLDER =  BASE_DIR / "entities"

#Load entity indexing
with open("feature_search/index_dictionary/entities_index.json",'r', encoding = "utf-8") as file:
    entity_index = json.load(file)

def get_entity_info(value: str, info:str):
    value = value.lower().strip()
    info = info.lower().strip()

    #Split features
    entities = re.split(
            r"\s*(?:,|\bor\b|\band\b)\s*",
            value
        )
    
    entities = [ entity.strip() for entity in entities if entity.strip()]
    
    results = {}
    not_found = []
    
    for entity in entities:
        files = entity_index["name_exact"].get(entity,[]) 
    
        if not files:
            files = entity_index["name_seperated"].get(entity,[])

        if not files:
            not_found.append(entity)
            continue

        #Get top file
        filename = files[0]
        
        yaml_path = ENTITY_YAML_FOLDER / filename
        
        with open( yaml_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        if info == "field_name":
            results[entity] = data.get("field_name","")

        elif info == 'type':
            results[entity] = data.get('type',"")

        elif info == 'description':
            results[entity] = data.get('description',"")

        elif info == 'business_logic':
            results[entity] = data.get('business_logic',"")

        else:
            results[entity] = (f"Unknown information type '{info}'.")
            
    return {
            "results": results,
            "info" : info,
            "not_found" : not_found   
            }
        
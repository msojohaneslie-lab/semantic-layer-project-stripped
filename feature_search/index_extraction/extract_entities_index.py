from pathlib import Path
import yaml
import json
import re

# CONFIG
YAML_FOLDER = Path(__file__).parent.parent / "entities"
INDEX_FILE = Path(__file__).parent.parent / "entities_index.json"


# TOKENIZER
def tokenize(text):
    """
    Convert text into searchable words.
    """

    if not text:
        return []

    text = str(text).lower()

    return re.findall(r"\b[\w]+\b", text)




# NAME NORMALIZER
def normalize_name(text):
  
    if not text:
        return ""

    text = str(text).lower().strip()

    # Treat underscore and hyphen as spaces
    text = re.sub(r"[_-]+", " ", text)

    # Remove repeated spaces
    text = re.sub(r"\s+", " ", text)

    return text


# ADD TO INDEX
def add_to_index(index, key, filename):
    """
    Add filename to an index entry without duplicates.
    """

    if not key:
        return

    if key not in index:
        index[key] = []

    if filename not in index[key]:
        index[key].append(filename)


# BUILD INDEXES

def build_indexes():

    indexes = {

        # FEATURE NAME

        "name_exact": {},
        "name_seperated": {},

        # GENERAL FEATURE INFORMATION
        "field_name": {},
        "field_name_seperated": {},
        "type": {},
        
    }


    # PROCESS EVERY YAML FILE
    for yaml_path in YAML_FOLDER.glob("*.yaml"):

        print(f"Indexing: {yaml_path.name}")

        # Read YAML
        with open(
            yaml_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = yaml.safe_load(file) or {}

        filename = yaml_path.name


        # 1. Entity Name
        entity_name = data.get(
            "name",
            ""
        )

        normalized_name = normalize_name(
            entity_name
        )

        #Exact Feature Name
        if entity_name:
            add_to_index(
                indexes["name_exact"],
                str(entity_name).lower().strip(),
                filename
            )
        #Seperated name
        if normalized_name:

            add_to_index(
                indexes["name_seperated"],
                normalized_name,
                filename
            )


        # 2. field_name
        field_name = data.get(
            "field_name",
            ""
        )

        normalized_field_name = normalize_name(
                    field_name
                )
        #Exact Name
        for word in tokenize(field_name):
            add_to_index(
                indexes["field_name"],
                word,
                filename
            )
        if normalized_field_name:
            add_to_index(
                indexes["field_name_seperated"],
                normalized_field_name,
                filename
            )

        # 3. Type
        type = data.get("type","")
        for word in tokenize(type):
            add_to_index(
                indexes["type"],
                word,
                filename
            )


    return indexes


# BUILD
indexes = build_indexes()


# SAVE
with open(
    INDEX_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        indexes,
        file,
        indent=2,
        ensure_ascii=False
    )


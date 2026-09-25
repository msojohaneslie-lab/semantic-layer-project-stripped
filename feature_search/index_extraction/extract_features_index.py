from pathlib import Path
import yaml
import json
import re


# CONFIG
YAML_FOLDER = Path(__file__).parent / "yaml_list"
INDEX_FILE = Path(__file__).parent / "feature_index.json"


# TOKENIZER
def tokenize(text):
    """
    Convert text into searchable words.
    """

    if not text:
        return []

    text = str(text).lower()

    return re.findall(r"\b[\w]+\b", text)


import re

def normalize_ttl(ttl):

    if not ttl:
        return []

    ttl = str(ttl).lower().strip()

    match = re.fullmatch(
        r"(\d+(?:\.\d+)?)\s*d",
        ttl
    )

    if not match:
        return [ttl]

    days = float(match.group(1))
    years = days / 365

    if days.is_integer():
        days = int(days)

    if years.is_integer():
        years = int(years)
    else:
        years = round(years, 2)

    return [
        f"{days}d",
        f"{years} years"
    ]

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


# ============================================================
# BUILD INDEXES
# ============================================================

def build_indexes():

    indexes = {

        # FEATURE NAME

        "name_exact": {},
        "name_words": {},
        "name_seperated": {},

        # GENERAL FEATURE INFORMATION
        "description": {},
        "entity": {},
        "domain": {},
        "tags": {},
        "ttl": {},



        "field_exact": {},
        "field_seperated": {},
        "field_words": {},


        # BUSINESS LOGIC
        "business_logic": {}
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



        # 1. FEATURE NAME
        feature_name = data.get(
            "name",
            ""
        )

        normalized_name = normalize_name(
            feature_name
        )

        if feature_name:
            add_to_index(
                indexes["name_exact"],
                feature_name,
                filename
            )
  
        #Exact Feature Name
        if normalized_name:

            add_to_index(
                indexes["name_seperated"],
                normalized_name,
                filename
            )


      
        #Seperate words
        for word in tokenize(normalized_name):
            add_to_index(
                indexes["name_words"],
                word,
                filename
            )


        # 2. DESCRIPTION
        description = data.get(
            "description",
            ""
        )
        for word in tokenize(description):

            add_to_index(
                indexes["description"],
                word,
                filename
            )


        # 3. ENTITY
        entity = data.get(
            "entity",
            ""
        )

        for word in tokenize(entity):
            add_to_index(
                indexes["entity"],
                word,
                filename
            )


        
        # 4. DOMAIN
        domain = data.get(
            "domain",
            ""
        )

        for word in tokenize(domain):
            add_to_index(
                indexes["domain"],
                word,
                filename
            )


        # 5. TAGS
        tags = data.get(
            "tags",
            []
        )

        for tag in tags:
            for word in tokenize(tag):
                add_to_index(
                    indexes["tags"],
                    word,
                    filename
                )
                
        # 6. ttl        
        ttl = data.get("ttl", "")

        for value in normalize_ttl(ttl):


                add_to_index(
                indexes["ttl"],
                value,
                filename
            )
      
        #7. Feature Fields
      
        feature_fields = data.get(
            "feature_fields",
            []
        )

        for field in feature_fields:

            field_name = field.get(
            "name",
            ""
        )

            if not field_name:
                continue

            add_to_index(
                indexes["field_exact"],
                field_name,
                filename
            )

  

            normalized_field = normalize_name(
                field_name
            )

            if not normalized_field:
                continue

            add_to_index(
                indexes["field_seperated"],
                normalized_field,
                filename
            )

    
            for word in tokenize(
                normalized_field
            ):

                add_to_index(
                    indexes["field_words"],
                    word,
                    filename
                )


# ====================================================
# 7. BUSINESS LOGIC
# ====================================================

    for field in feature_fields:

        business_logic = field.get(
            "business_logic",
            ""
        )

        for word in tokenize(
            business_logic
        ):

            add_to_index(
                indexes["business_logic"],
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



# DONE
print()
print("===================================")
print("Structured feature index created!")
print("===================================")

print(
    "Feature names:",
    len(indexes["name_exact"])
)

print(
    "Feature name words:",
    len(indexes["name_words"])
)

print(
    "Fields:",
    len(indexes["field_exact"])
)

print(
    "Field words:",
    len(indexes["field_words"])
)

print(
    "Description words:",
    len(indexes["description"])
)

print(
    "Entity words:",
    len(indexes["entity"])
)

print(
    "Domain words:",
    len(indexes["domain"])
)

print(
    "Tags:",
    len(indexes["tags"])
)

print(
    "Business logic words:",
    len(indexes["business_logic"])
)
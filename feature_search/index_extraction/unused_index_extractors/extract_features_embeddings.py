import json
import time
from pathlib import Path

import yaml
from google import genai
from dotenv import load_dotenv
import os


# CONFIG
BASE_DIR = Path(__file__).resolve().parents[2]

YAML_FOLDER = BASE_DIR / "yaml_list"

OUTPUT_FILE = BASE_DIR / "feature_semantic_index.json"

MODEL = "gemini-embedding-001"

REQUEST_DELAY = 1
MAX_RETRIES = 3
RETRY_DELAY = 5


# GEMINI CLIENT
BASE_DIR = Path(__file__).parent.parent

load_dotenv(BASE_DIR / ".env")

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))



# SAVE INDEX
def save_index(semantic_index):

    temp_file = OUTPUT_FILE.with_suffix(".tmp")

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            semantic_index,
            f,
            indent=2,
            ensure_ascii=False
        )

    # Replace the existing file safely
    temp_file.replace(OUTPUT_FILE)


# ============================================================
# LOAD EXISTING INDEX
# ============================================================

def load_index():

    if not OUTPUT_FILE.exists():

        print(
            "No existing feature_semantic_index.json found."
        )

        print(
            "Starting from empty index."
        )

        return []


    print(
        f"Loading existing index: "
        f"{OUTPUT_FILE.name}"
    )

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            semantic_index = json.load(f)


        if not isinstance(
            semantic_index,
            list
        ):

            print(
                "Existing index is not a list."
            )

            print(
                "Starting from empty index."
            )

            return []


        print(
            f"Loaded {len(semantic_index)} "
            f"existing embeddings."
        )

        return semantic_index


    except json.JSONDecodeError:

        print(
            "ERROR: feature_semantic_index.json "
            "is invalid."
        )

        return []


# CREATE EMBEDDING
def create_embedding(text):

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = client.models.embed_content(
                model=MODEL,
                contents=text,
            )

            return response.embeddings[0].values


        except Exception as e:

            error_message = str(e)

            print(
                f"Embedding error "
                f"(attempt {attempt}/{MAX_RETRIES})"
            )

            print(error_message)


            # ------------------------------------------------
            # RESOURCE EXHAUSTED
            # ------------------------------------------------

            if (
                "RESOURCE_EXHAUSTED"
                in error_message

                or "429"
                in error_message

                or "quota"
                in error_message.lower()
            ):

                raise RuntimeError(
                    "RESOURCE_EXHAUSTED"
                )


            # ------------------------------------------------
            # RETRY OTHER ERRORS
            # ------------------------------------------------

            if attempt < MAX_RETRIES:

                print(
                    f"Retrying in "
                    f"{RETRY_DELAY} seconds..."
                )

                time.sleep(
                    RETRY_DELAY
                )

            else:

                raise


# BUILD PROCESSED SET
def build_processed_set(semantic_index):
    processed = set()
    for item in semantic_index:
        feature = item.get("feature")
        feature_view = item.get("feature_view")

        if feature and feature_view:
            processed.add((feature, feature_view))
    return processed


# BUILD INDEX
def build_feature_semantic_index():


    # LOAD EXISTING INDEX
    semantic_index = load_index()


    # FIND ALREADY PROCESSED FEATURES
    processed = build_processed_set(semantic_index)


    print(
        f"Already processed: "
        f"{len(processed)}"
    )


    # FIND YAML FILES
    yaml_files = list(YAML_FOLDER.rglob("*.yaml"))

    yaml_files += list(YAML_FOLDER.rglob("*.yml"))

    # Remove duplicates
    yaml_files = list(dict.fromkeys(yaml_files))


    print(
        f"Found {len(yaml_files)} YAML files."
    )


    # PROCESS YAML FILES
    for yaml_number, yaml_file in enumerate(yaml_files,start=1):

        # LOAD YAML
        try:
            with open(yaml_file,"r",encoding="utf-8") as f:
                data = yaml.safe_load(f)


        except:
            continue

        # FEATURE VIEW
        feature_view = data.get("name")

        if not feature_view:
            continue
        
        # ENTITY
        entity = data.get("entity")


        # FEATURE FIELDS
        feature_fields = data.get("feature_fields",[])

        # PROCESS EACH FEATURE
        for field in feature_fields:
            if not isinstance(field,dict):
                continue


            feature = field.get("name")

            if not feature:
                continue


            # CHECK WHETHER ALREADY EMBEDDED
            key = (feature,feature_view)


            if key in processed:

                print(
                    f"SKIP: {feature} "
                    f"[{feature_view}] "
                    "already embedded."
                )

                continue


            # GET DESCRIPTION
            description = field.get("description")

            if description is None:
                description = ""

            else:
                description = str(description).strip()


            # GET BUSINESS LOGIC
            business_logic = field.get("business_logic")

            if business_logic is None:
                business_logic = ""

            else:
                business_logic = str(business_logic).strip()


            # NOTHING TO EMBED
            if (not description and not business_logic):
                continue


            # CREATE TEXT
            semantic_text = (
                f"Description: {description}\n"
                f"Business Logic: {business_logic}"
            )


            print(f"Embedding: {feature}")
            print(f"Feature view: {feature_view}")


            # CREATE EMBEDDING
            try:
                embedding = create_embedding(semantic_text)


            except RuntimeError as e:

                if (
                    str(e)
                    == "RESOURCE_EXHAUSTED"
                ):

                    print()
                    print(
                        "=========================================="
                    )

                    print(
                        "RESOURCE EXHAUSTED"
                    )

                    print(
                        "Stopping safely."
                    )

                    print(
                        f"Saved embeddings: "
                        f"{len(semantic_index)}"
                    )

                    print(
                        "Run the script again later "
                        "to continue."
                    )

                    print(
                        "=========================================="
                    )

                    return

                raise


            except Exception as e:
                continue


            # CREATE ENTRY
            entry = {
                "feature": feature,
                "feature_view": feature_view,
                "entity": entity,
                "description": description,
                "business_logic": business_logic,
                "embedding": embedding,
            }


            # ADD TO INDEX
            semantic_index.append(entry)
            processed.add(key)

            # SAVE IMMEDIATELY
            save_index(semantic_index)

            time.sleep(REQUEST_DELAY)


# MAIN
if __name__ == "__main__":

    build_feature_semantic_index()
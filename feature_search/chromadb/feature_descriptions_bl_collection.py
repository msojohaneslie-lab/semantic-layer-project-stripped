from pathlib import Path
from dotenv import load_dotenv
import os
import chromadb
import yaml
from google import genai
import time


# PATHS
BASE_DIR = Path(__file__).resolve().parents[1]

YAML_FOLDER = BASE_DIR / "yaml_list"
CHROMA_FOLDER = BASE_DIR / "chromadb"
COLLECTION_NAME = "feature_description_bl_collection"


# ENVIRONMENT
load_dotenv(BASE_DIR / ".env")
api_key = os.getenv("GOOGLE_API_KEY")

# CLIENTS
genai_client = genai.Client(api_key=api_key)
chroma_client = chromadb.PersistentClient(path=str(CHROMA_FOLDER))


# GET OR CREATE COLLECTION
try:
    collection = chroma_client.get_collection(name=COLLECTION_NAME)

except Exception:
    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        configuration={
            "hnsw": {
                "space": "cosine"
            }
        }
    )

# EMBEDDING FUNCTION
def generate_embedding(text, max_retries=5):

    for attempt in range(max_retries):
        try:
            response = genai_client.models.embed_content(
                model="gemini-embedding-001",
                contents=text
            )
            return response.embeddings[0].values

        except Exception as e:
            error_message = str(e)
            if "429" not in error_message:
                raise

            wait_time = 10 * (attempt + 1)
            print(
                f"429 RESOURCE_EXHAUSTED. "
                f"Waiting {wait_time} seconds..."
            )

            time.sleep(wait_time)

    raise RuntimeError(
        "Embedding failed after maximum retries."
    )


# PROCESS YAML FILES
yaml_files = list(YAML_FOLDER.glob("*.yaml"))

for yaml_index, yaml_path in enumerate( yaml_files,start=1):
    # LOAD YAML
    try:
        with open(yaml_path,"r",encoding="utf-8") as file:
            yaml_data = yaml.safe_load(file)

    except Exception as e:
        print("error")
        continue


    # FEATURE VIEW INFORMATION
    feature_view_name = (yaml_data.get("name"))
    entity = (yaml_data.get("entity"))
    feature_fields = (yaml_data.get("feature_fields"))


    # PROCESS EACH FIELD
    for field in feature_fields:
        field_name = field.get("name")
        description = (field.get("description"))
        business_logic = (field.get("business_logic"))


        record_id = (
            f"{field_name}"
            f"__{entity}"
            f"__{yaml_path.stem}"
        )


        
        # CHECKPOINT
        existing = collection.get(
            ids=[record_id],
            include=[]
        )

        if existing["ids"]:
            print(f" SKIP {field_name} ")
            continue


        # CREATE EMBEDDING TEXT
        embedding_text = (
            f"Description: {description}\n"
            f"Business Logic: {business_logic}"
        )


        # GENERATE EMBEDDING
        try:
            embedding = generate_embedding(embedding_text)

        except Exception as e:
            print(f"  ERROR embedding {field_name}: {e}")
            continue


        # SAVE IMMEDIATELY TO CHROMA
        try:
            collection.upsert(
                ids=[record_id],
                embeddings=[embedding],
                documents=[description],
                metadatas=[{
                    "field_name": field_name,
                    "entity": entity,
                    "yaml_file": yaml_path.name,
                    "feature_view": feature_view_name,
                    "business_logic": business_logic,
                }]
            )

            print(f"SAVED: {field_name}")

        except Exception as e:
            print(f"  ERROR saving {field_name}: {e}")
            continue
    print()

print("finsihed finally")
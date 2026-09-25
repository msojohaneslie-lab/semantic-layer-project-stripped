from pathlib import Path
from dotenv import load_dotenv
import os
import chromadb
import yaml
from google import genai


# CONFIG
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")
YAML_FOLDER = BASE_DIR / "yaml_list"
CHROMA_FOLDER = BASE_DIR / "chromadb"

COLLECTION_NAME = "feature_views_descriptions"


# GEMINI CLIENT
api_key = os.getenv("GOOGLE_API_KEY")
genai_client = genai.Client(api_key=api_key)

# CONNECT TO CHROMA
chroma_client = chromadb.PersistentClient( path=str(CHROMA_FOLDER))


# If the collection already exists, delete it
# so we can rebuild it from scratch.
try:
    chroma_client.delete_collection(COLLECTION_NAME)
    print(f"Deleted existing collection: {COLLECTION_NAME}")
except Exception:
    pass


collection = chroma_client.create_collection(
    name=COLLECTION_NAME,
    configuration={
        "hnsw": {
            "space": "cosine"
        }
    }
)

# PROCESS YAML FILES
ids = []
embeddings = []
documents = []
metadatas = []


yaml_files = list(YAML_FOLDER.glob("*.yaml"))

print(f"Found {len(yaml_files)} YAML files")
print()


for index, yaml_path in enumerate(yaml_files, start=1):
    # Load YAML
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

    except Exception as e:
        print("error")
        continue

    # Get YAML information
    feature_view_name = yaml_data.get("name")
    description = yaml_data.get("description")
    entity = yaml_data.get("entity")


    # Generate embedding
    try:

        response = genai_client.models.embed_content(
            model="gemini-embedding-001",
            contents=description
        )

        embedding = response.embeddings[0].values

    except Exception as e:
        print("error")
        continue


    # Prepare Chroma record

    record_id = yaml_path.name
    ids.append(record_id)
    embeddings.append(embedding)
    documents.append(description)
    metadatas.append({
        "yaml_file": yaml_path.name,
        "feature_view": feature_view_name,
        "entity": entity,
    })

# INSERT INTO CHROMA
if ids:
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )

print(f"Collection : {collection.name}")
print(f"Records    : {collection.count()}")

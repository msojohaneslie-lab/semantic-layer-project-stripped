import chromadb
from pathlib import Path
OLD_NAME = "feature_fields_descriptions"
NEW_NAME = "feature_description_bl_collection"
BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_FOLDER = BASE_DIR / "chromadb"
INNER_CHROMA_FOLDER = BASE_DIR / "chromadb" / "chromadb"

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_FOLDER)
)

outer_chroma_client = chromadb.PersistentClient(path = str(INNER_CHROMA_FOLDER))

old_collection = outer_chroma_client(OLD_NAME)

new_collection = chroma_client.create_collection(
    name=NEW_NAME,
    configuration={
        "hnsw": {
            "space": "cosine"
        }
    }
)


data = old_collection.get(
    include=[
        "embeddings",
        "documents",
        "metadatas"
    ]
)

new_collection.upsert(
    ids=data["ids"],
    embeddings=data["embeddings"],
    documents=data["documents"],
    metadatas=data["metadatas"]
)

print("Old:", old_collection.count())
print("New:", new_collection.count())
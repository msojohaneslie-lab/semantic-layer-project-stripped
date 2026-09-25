import chromadb
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_FOLDER = BASE_DIR / "chromadb" 

client = chromadb.PersistentClient(path=str(CHROMA_FOLDER))

collection = client.get_collection(name="entities_description_bl_collection")

data = collection.get(
    include=["embeddings", "documents", "metadatas"]
)

# print(data)
print(collection.count())
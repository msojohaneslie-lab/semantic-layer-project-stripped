import time
import hashlib
from pathlib import Path
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os



# CONFIG
BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_FOLDER = BASE_DIR / "chromadb"
INPUT_FILE = BASE_DIR / "SQL_parser" / "reconstructed_sql.json"
COLLECTION_NAME = "sql_embeddings_collection"
MODEL = "gemini-embedding-001"
BATCH_SIZE = 20
BATCH_DELAY = 30
OUTPUT_DIMENSIONALITY = 3072
env = load_dotenv(BASE_DIR / ".env")
api_key = os.getenv("GOOGLE_API_KEY")
# CLIENTS

genai_client = genai.Client(api_key=api_key)
chroma_client = chromadb.PersistentClient(path=str(CHROMA_FOLDER))


# GET / CREATE COLLECTION
try:
    collection = chroma_client.get_collection(name=COLLECTION_NAME)
    print(
        f"Using existing collection: "
        f"{COLLECTION_NAME}"
    )

except Exception:
    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        configuration={
            "hnsw": {
                "space": "cosine"
            }
        }
    )

    print(f"Created collection:{COLLECTION_NAME}")


# NORMALIZE SQL
def normalize_sql(sql):

    if sql is None:
        return ""
    if not isinstance(sql, str):
        sql = str(sql)
    sql = sql.strip()
    if not sql:
        return ""
    sql = " ".join(sql.split())
    return sql


# CREATE TEXT TO EMBED
def create_embedding_text(document):
    sql = document.get("sql", "")
    return normalize_sql(sql)


# CREATE STABLE CHROMA ID
def get_document_key(document):
    return (
        document.get("field"),
        document.get("entity")
    )


def get_chroma_id(document):
    key = get_document_key(document)
    raw_key = "||".join(
        "" if value is None else str(value)
        for value in key
    )

    # Stable ID.
    # Same field/entity/feature/file
    # always produces the same ID.
    return hashlib.sha256(
        raw_key.encode("utf-8")
    ).hexdigest()


# VALIDATE DOCUMENT
def is_valid_sql_document(document):
    sql = create_embedding_text(document)
    return bool(sql)


# GENERATE EMBEDDINGS
def embed_batch(documents):
    texts = []
    for document in documents:
        sql = create_embedding_text(document)
        if not sql:
            raise ValueError(
                "Empty SQL found in batch:\n"
                f"Field   : {document.get('field')}\n"
                f"Entity  : {document.get('entity')}\n"
                f"Feature : {document.get('feature')}\n"
                f"File    : {document.get('file')}\n"
                f"Raw SQL : {repr(document.get('sql'))}"
            )

        texts.append(sql)

    print(
        f"Sending {len(texts)} SQLs to Gemini..."
    )

    response = genai_client.models.embed_content(
        model=MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY",
            output_dimensionality=OUTPUT_DIMENSIONALITY
        )
    )

    if not response.embeddings:
        raise ValueError(
            "Gemini returned no embeddings."
        )

    if len(response.embeddings) != len(documents):
        raise ValueError(
            f"Expected {len(documents)} embeddings, "
            f"but received {len(response.embeddings)}."
        )

    return [
        embedding.values
        for embedding in response.embeddings
    ]


# CHECK WHICH DOCUMENTS ALREADY EXIST
def get_pending_documents(documents):

    pending = []

    for document in documents:

        record_id = get_chroma_id(document)

        existing = collection.get(
            ids=[record_id],
            include=[]
        )

        if existing["ids"]:
            print(
                f"SKIP: "
                f"{document.get('field')} | "
                f"{document.get('feature')}"
            )
            continue
        pending.append(document)
    return pending


# SAVE BATCH TO CHROMA
def save_batch_to_chroma(documents, embeddings):
    ids = []
    documents_text = []
    metadatas = []

    for document in documents:
        record_id = get_chroma_id(document)
        sql = create_embedding_text(document)
        ids.append(record_id)
        documents_text.append(sql)

        metadatas.append({"field": str(document.get("field") or ""),
            "entity": str(document.get("entity") or ""),
            "feature": str(document.get("feature") or ""),
            "file": str(document.get("file") or ""),
        })

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents_text,
        metadatas=metadatas,
    )


# MAIN
def main():

    # LOAD INPUT
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        input_documents = __import__("json").load(f)

    # NORMALIZE + VALIDATE SQL
    valid_documents = []
    invalid_documents = []

    for index, document in enumerate(input_documents):
        sql = create_embedding_text(document)

        if not sql:
            invalid_documents.append((index,document))
            continue

        # Use normalized SQL
        # for the current document.
        document["sql"] = sql
        valid_documents.append(document)

    print(
        f"Valid SQLs   : "
        f"{len(valid_documents)}"
    )

    print(
        f"Invalid SQLs : "
        f"{len(invalid_documents)}"
    )


    # INVALID SQL DETAILS
    if invalid_documents:
        print("INVALID / EMPTY SQL RECORDS")
        for index, document in invalid_documents:
        
            print(f"Field: {document.get('field')}")
            print(f"Entity: {document.get('entity')}")


    # STOP IF NOTHING TO EMBED
    if not valid_documents:
        print("No valid SQLs found.")
        return

    # FIND PENDING DOCUMENTS
    print("CHECKING CHROMA CHECKPOINT")
    pending = get_pending_documents(valid_documents)
    print(f"Remaining: {len(pending)}")

    # NOTHING LEFT
    if not pending:
        print("All SQLs already exist in ChromaDB.")
        return


    # EMBEDDING LOOP
    batch_number = 0
    while pending:

        batch = pending[:BATCH_SIZE]
        batch_number += 1

        print(
            f"Embedding batch "
            f"{batch_number}"
        )

        print(
            f"Batch size : "
            f"{len(batch)}"
        )

        print(
            f"Remaining  : "
            f"{len(pending)}"
        )

        # GENERATE EMBEDDINGS
        try:
            embeddings = embed_batch(batch)
            # SAVE IMMEDIATELY TO CHROMA
            save_batch_to_chroma(batch,embeddings)

            # Remove successfully processed
            # documents from pending.
            pending = pending[len(batch):]


            # WAIT
            if pending:
                print(f"Waiting {BATCH_DELAY} seconds...")
                time.sleep(BATCH_DELAY)


        except ValueError as e:

            # VALIDATION ERROR
            print()
            print(
                f"VALIDATION ERROR: {e}"
            )

            print()
            print("Trying SQLs individually...")


            bad_document_found = False

            remaining_batch = []
            for document in batch:
                try:
                    single_embedding = (embed_batch([document]))
                    save_batch_to_chroma([document],single_embedding)

                    print(
                        f"{document.get('field')} | "
                        f"{document.get('feature')}"
                    )


                except Exception as single_error:
                    print("FAILED:")
                    print(f"Field: {document.get('field')} - Entity: {document.get('entity')}")
                    bad_document_found = True


            # The entire batch was already handled
            # individually.
            pending = pending[
                len(batch):
            ]


            if bad_document_found:

                print()
                print(
                    "Some SQLs could not "
                    "be embedded."
                )

            continue


        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")

            print(f"Waiting {BATCH_DELAY}seconds before retry...")
            time.sleep(BATCH_DELAY)

            # IMPORTANT:
            #
            # Do NOT remove the batch from
            # pending.
            #
            # It will be retried.

            continue


    # FINAL STATISTICS
    print()
    print(f"Chroma collection :{collection.name}")

if __name__ == "__main__":
    main()
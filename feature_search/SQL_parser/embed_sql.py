import json
import time
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv
import os


# CONFIG
INPUT_FILE = Path("reconstructed_sql.json")

OUTPUT_FILE = Path("sql_embeddings.json")

# Gemini embedding model
MODEL = "gemini-embedding-001"

# Number of SQLs sent in one embedding request
BATCH_SIZE = 20

# Wait between successful batches / retries
BATCH_DELAY = 30

# Embedding dimensionality
OUTPUT_DIMENSIONALITY = 3072


# CLIENT
BASE_DIR = Path(__file__).parent.parent

load_dotenv(BASE_DIR / ".env")

client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY")
)




# ============================================================
# NORMALIZE SQL
# ============================================================

def normalize_sql(sql):
    """
    Normalize SQL whitespace.

    Example:

        SELECT
            id,
            customer_id
        FROM customers
        WHERE status = 'active'

    becomes:

        SELECT id, customer_id FROM customers WHERE status = 'active'
    """

    if sql is None:
        return ""

    # Make sure we are working with a string
    if not isinstance(sql, str):
        sql = str(sql)

    sql = sql.strip()

    if not sql:
        return ""

    # Replace:
    #   newlines
    #   tabs
    #   multiple spaces
    #
    # with one space.
    sql = " ".join(sql.split())

    return sql


# ============================================================
# CREATE TEXT TO EMBED
# ============================================================

def create_embedding_text(document):
    """
    Create the exact SQL text that will be embedded.

    Only SQL is embedded.

    No:
        field
        entity
        feature
        SQL: prefix
    """

    sql = document.get("sql", "")

    return normalize_sql(sql)


# ============================================================
# VALIDATE DOCUMENT
# ============================================================

def get_document_key(document):
    """
    Create a stable key for identifying a document.
    """

    return (
        document.get("field"),
        document.get("entity"),
        document.get("feature"),
        document.get("file")
    )


def is_valid_sql_document(document):
    """
    Returns True if the document contains non-empty SQL
    after normalization.
    """

    sql = create_embedding_text(document)

    return bool(sql)


# ============================================================
# EMBED A BATCH
# ============================================================

def embed_batch(documents):
    """
    Generate embeddings for a batch of documents.

    Every document is checked for non-empty SQL before
    being sent to Gemini.
    """

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

    response = client.models.embed_content(
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


# ============================================================
# SAVE OUTPUT
# ============================================================

def save_embeddings(documents):
    """
    Save embeddings safely.

    Writes to a temporary file first, then replaces
    the real output file.
    """

    temp_file = OUTPUT_FILE.with_suffix(".tmp")

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            documents,
            f,
            indent=2,
            ensure_ascii=False
        )

    temp_file.replace(
        OUTPUT_FILE
    )


# ============================================================
# LOAD CHECKPOINT
# ============================================================

def load_checkpoint(input_documents):
    """
    Load an existing embedding checkpoint.

    Existing embeddings are matched using:

        field
        entity
        feature
        file

    SQL is always taken from the CURRENT input file.
    """

    if not OUTPUT_FILE.exists():

        print(
            "No existing checkpoint found."
        )

        return [
            {
                "field": document.get("field"),
                "entity": document.get("entity"),
                "feature": document.get("feature"),
                "file": document.get("file"),
                "sql": create_embedding_text(document),
                "embedding": None
            }
            for document in input_documents
        ]

    print(
        f"Found existing {OUTPUT_FILE}."
    )

    print(
        "Loading embedding checkpoint..."
    )

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        existing = json.load(f)

    # --------------------------------------------------------
    # Create lookup
    # --------------------------------------------------------

    existing_lookup = {}

    for document in existing:

        key = get_document_key(document)

        existing_lookup[key] = document

    # --------------------------------------------------------
    # Rebuild output using CURRENT input
    # --------------------------------------------------------

    output = []

    reused = 0
    reset = 0

    for document in input_documents:

        key = get_document_key(document)

        current_sql = create_embedding_text(
            document
        )

        previous = existing_lookup.get(key)

        # ----------------------------------------------------
        # Existing embedding
        # ----------------------------------------------------

        if previous:

            previous_embedding = previous.get(
                "embedding"
            )

            if previous_embedding:

                output.append({
                    "field": document.get("field"),
                    "entity": document.get("entity"),
                    "feature": document.get("feature"),
                    "file": document.get("file"),
                    "sql": current_sql,
                    "embedding": previous_embedding
                })

                reused += 1

                continue

        # ----------------------------------------------------
        # No existing embedding
        # ----------------------------------------------------

        output.append({
            "field": document.get("field"),
            "entity": document.get("entity"),
            "feature": document.get("feature"),
            "file": document.get("file"),
            "sql": current_sql,
            "embedding": None
        })

        reset += 1

    print(
        f"Reused embeddings : {reused}"
    )

    print(
        f"Need embedding    : {reset}"
    )

    return output


# ============================================================
# FIND INVALID SQL
# ============================================================

def find_invalid_sql(documents):
    """
    Find documents whose SQL is empty after normalization.
    """

    invalid = []

    for index, document in enumerate(documents):

        sql = create_embedding_text(
            document
        )

        if not sql:

            invalid.append(
                (
                    index,
                    document
                )
            )

    return invalid


# ============================================================
# PRINT INVALID SQL
# ============================================================

def print_invalid_sql(invalid):
    """
    Print detailed information about invalid SQL records.
    """

    if not invalid:

        print(
            "No empty SQL records found."
        )

        return

    print()
    print("=" * 70)
    print("INVALID / EMPTY SQL RECORDS")
    print("=" * 70)

    for index, document in invalid:

        print()
        print(
            f"Index   : {index}"
        )

        print(
            f"Field   : {document.get('field')}"
        )

        print(
            f"Entity  : {document.get('entity')}"
        )

        print(
            f"Feature : {document.get('feature')}"
        )

        print(
            f"File    : {document.get('file')}"
        )

        print(
            f"Raw SQL : {repr(document.get('sql'))}"
        )

    print()
    print(
        f"Total invalid SQLs: {len(invalid)}"
    )

    print("=" * 70)
    print()


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # LOAD INPUT
    # ========================================================

    print(
        f"Loading {INPUT_FILE}..."
    )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        input_documents = json.load(f)

    print(
        f"Loaded {len(input_documents)} documents."
    )


    # ========================================================
    # NORMALIZE + VALIDATE SQL
    # ========================================================

    print()
    print("=" * 70)
    print("VALIDATING SQL")
    print("=" * 70)

    valid_documents = []

    invalid_documents = []

    for index, document in enumerate(
        input_documents
    ):

        sql = create_embedding_text(
            document
        )

        # ----------------------------------------------------
        # Empty SQL
        # ----------------------------------------------------

        if not sql:

            invalid_documents.append(
                (
                    index,
                    document
                )
            )

            continue

        # ----------------------------------------------------
        # Store normalized SQL
        # ----------------------------------------------------

        document["sql"] = sql

        valid_documents.append(
            document
        )

    print(
        f"Valid SQLs   : {len(valid_documents)}"
    )

    print(
        f"Invalid SQLs : {len(invalid_documents)}"
    )

    print("=" * 70)


    # ========================================================
    # PRINT INVALID SQL DETAILS
    # ========================================================

    print_invalid_sql(
        invalid_documents
    )


    # ========================================================
    # STOP IF NOTHING TO EMBED
    # ========================================================

    if not valid_documents:

        print(
            "No valid SQLs found."
        )

        return


    # ========================================================
    # LOAD CHECKPOINT
    # ========================================================

    documents = load_checkpoint(
        valid_documents
    )

    total = len(documents)


    # ========================================================
    # STATISTICS
    # ========================================================

    completed = sum(
        1
        for document in documents
        if document.get("embedding")
    )

    remaining = total - completed

    print()
    print("=" * 70)

    print(
        f"Total SQLs       : {total}"
    )

    print(
        f"Already embedded : {completed}"
    )

    print(
        f"Remaining        : {remaining}"
    )

    print(
        f"Batch size       : {BATCH_SIZE}"
    )

    print(
        f"Embedding size   : {OUTPUT_DIMENSIONALITY}"
    )

    print("=" * 70)
    print()


    # ========================================================
    # NOTHING LEFT
    # ========================================================

    if remaining == 0:

        print(
            "All SQLs already have embeddings."
        )

        return


    # ========================================================
    # EMBEDDING LOOP
    # ========================================================

    batch_number = 0

    while True:

        # ----------------------------------------------------
        # Find pending documents
        # ----------------------------------------------------

        pending = [
            document
            for document in documents
            if not document.get("embedding")
        ]

        if not pending:

            break

        batch = pending[
            :BATCH_SIZE
        ]

        batch_number += 1

        print()
        print("-" * 70)

        print(
            f"Embedding batch {batch_number}"
        )

        print(
            f"Batch size : {len(batch)}"
        )

        print(
            f"Remaining  : {len(pending)}"
        )

        print("-" * 70)


        # ----------------------------------------------------
        # Generate embeddings
        # ----------------------------------------------------

        try:

            embeddings = embed_batch(
                batch
            )


            # ------------------------------------------------
            # Attach embeddings
            # ------------------------------------------------

            for document, embedding in zip(
                batch,
                embeddings
            ):

                document["embedding"] = embedding

                print(
                    f"    OK: "
                    f"{document.get('field')} | "
                    f"{document.get('feature')}"
                )


            # ------------------------------------------------
            # Save checkpoint
            # ------------------------------------------------

            save_embeddings(
                documents
            )

            print()

            print(
                f"Saved checkpoint to "
                f"{OUTPUT_FILE}"
            )


            # ------------------------------------------------
            # Wait before next batch
            # ------------------------------------------------

            pending_after = [
                document
                for document in documents
                if not document.get("embedding")
            ]

            if pending_after:

                print()

                print(
                    f"Waiting {BATCH_DELAY} seconds..."
                )

                time.sleep(
                    BATCH_DELAY
                )


        except ValueError as e:

            # ------------------------------------------------
            # Permanent validation error
            # ------------------------------------------------

            print()
            print(
                f"VALIDATION ERROR: {e}"
            )

            print()
            print(
                "This batch contains invalid data."
            )

            print(
                "Trying individual SQLs to identify "
                "the problematic record..."
            )


            # ------------------------------------------------
            # Try each document individually
            # ------------------------------------------------

            bad_document_found = False

            for document in batch:

                try:

                    single_embedding = embed_batch(
                        [document]
                    )

                    document["embedding"] = (
                        single_embedding[0]
                    )

                    print(
                        f"    OK: "
                        f"{document.get('field')} | "
                        f"{document.get('feature')}"
                    )

                    save_embeddings(
                        documents
                    )

                except Exception as single_error:

                    print()
                    print(
                        "    FAILED:"
                    )

                    print(
                        f"      Field   : "
                        f"{document.get('field')}"
                    )

                    print(
                        f"      Entity  : "
                        f"{document.get('entity')}"
                    )

                    print(
                        f"      Feature : "
                        f"{document.get('feature')}"
                    )

                    print(
                        f"      File    : "
                        f"{document.get('file')}"
                    )

                    print(
                        f"      SQL     : "
                        f"{repr(document.get('sql'))}"
                    )

                    print(
                        f"      Error   : "
                        f"{single_error}"
                    )

                    bad_document_found = True

                    # ------------------------------------------------
                    # Mark permanently bad record as failed
                    # ------------------------------------------------

                    document["embedding"] = []

            # ------------------------------------------------
            # Save after individual processing
            # ------------------------------------------------

            save_embeddings(
                documents
            )

            if bad_document_found:

                print()
                print(
                    "Problematic SQLs were skipped."
                )

            continue


        except Exception as e:

            # ------------------------------------------------
            # API / temporary error
            # ------------------------------------------------

            print()

            print(
                f"ERROR: {type(e).__name__}: {e}"
            )

            print(
                "No embeddings from this batch "
                "were marked as completed."
            )

            print(
                f"Waiting {BATCH_DELAY} seconds "
                "before retry..."
            )

            time.sleep(
                BATCH_DELAY
            )

            continue


    # ========================================================
    # FINAL STATISTICS
    # ========================================================

    completed = sum(
        1
        for document in documents
        if document.get("embedding")
    )

    failed = total - completed

    print()
    print("=" * 70)
    print("EMBEDDING FINISHED")
    print("=" * 70)

    print(
        f"Total     : {total}"
    )

    print(
        f"Completed : {completed}"
    )

    print(
        f"Failed    : {failed}"
    )

    print(
        f"Output    : {OUTPUT_FILE}"
    )

    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
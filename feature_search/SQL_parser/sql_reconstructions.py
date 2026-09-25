import json
import time
from pathlib import Path
from google import genai
import sqlglot
from dotenv import load_dotenv
import os

# ============================================================
# CONFIG
# ============================================================

INPUT_FILE = Path("field_sql_index.json")

# The ONLY output file
OUTPUT_FILE = Path("reconstructed_sql.json")

MODEL = "gemini-3.5-flash-lite"

# Number of SQLs before a longer pause
BATCH_SIZE = 20

# Delay between individual Gemini requests
REQUEST_DELAY = 2

# Delay after each batch
BATCH_DELAY = 120


# GEMINI CLIENT
BASE_DIR = Path(__file__).parent.parent

load_dotenv(BASE_DIR / ".env")

client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY")
)


# CREATE FLAT DOCUMENTS
def create_documents(sql_index):
    """
    Convert the original field-based index into a flat list.

    The structure is NOT stored in the output file.
    It is only kept in memory while processing.

    Original:

        FieldA:
          - feature1
            entity
            file
            sql:
              structure

          - feature2
            entity
            file
            sql:
              structure

    Output:

        [
            {
                "field": "...",
                "feature": "...",
                "entity": "...",
                "file": "...",
                "sql": null
            }
        ]
    """

    documents = []

    for field_name, entries in sql_index.items():

        for entry in entries:

            sql_data = entry.get("sql", {})

            document = {
                "field": field_name,
                "feature": entry.get("feature"),
                "entity": entry.get("entity"),
                "file": entry.get(
                    "file",
                    entry.get("yaml_file")
                ),

                # Structure is kept ONLY in memory.
                "_structure": sql_data.get("structure"),

                # Reconstructed SQL.
                "sql": None
            }

            documents.append(document)

    return documents


# LOAD / CREATE OUTPUT
def load_documents(sql_index):
    """
    If reconstructed_sql.json already exists, load the
    checkpoint.

    Otherwise create it from the original index.

    The structure is always recovered from the ORIGINAL
    field_sql_index3.json, not stored in the output file.
    """

    if OUTPUT_FILE.exists():

        print(
            f"Found existing {OUTPUT_FILE}"
        )

        print(
            "Loading checkpoint..."
        )

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            documents = json.load(f)

        # ----------------------------------------------------
        # Recover structures from original index
        # ----------------------------------------------------

        original_documents = create_documents(
            sql_index
        )

        if len(documents) != len(original_documents):

            raise ValueError(
                "The number of documents in reconstructed_sql.json "
                "does not match the original SQL index."
            )

        for document, original in zip(
            documents,
            original_documents
        ):

            document["_structure"] = original["_structure"]

        return documents

    # --------------------------------------------------------
    # First run
    # --------------------------------------------------------

    print(
        f"Loading {INPUT_FILE}..."
    )

    documents = create_documents(
        sql_index
    )

    # Save initial checkpoint immediately
    save_documents(documents)

    return documents


# ============================================================
# SAVE
# ============================================================

def save_documents(documents):

    output_documents = []

    for document in documents:

        output_documents.append({
            "field": document.get("field"),
            "feature": document.get("feature"),
            "entity": document.get("entity"),
            "file": document.get("file"),
            "sql": document.get("sql")
        })

    # Write safely to a temporary file first.
    temp_file = OUTPUT_FILE.with_suffix(".tmp")

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output_documents,
            f,
            indent=2,
            ensure_ascii=False
        )

    # Replace old checkpoint
    temp_file.replace(OUTPUT_FILE)


# GEMINI RECONSTRUCTION
def reconstruct_sql(document):
    """
    Reconstruct SQL from the sqlglot structure.
    """

    structure = document.get("_structure")

    if not structure:

        raise ValueError(
            "SQL structure is empty"
        )

    prompt = f"""
You are reconstructing SQL from a structured representation
that was extracted programmatically from an existing SQL query.

Your ONLY task is to reconstruct the SQL represented by the
structure.

STRICT RULES:

1. Return ONLY SQL.
2. Do not return markdown.
3. Do not use ```sql.
4. Do not explain anything.
5. Do not add comments.
6. Do not invent tables.
7. Do not invent columns.
8. Do not invent joins.
9. Do not invent filters.
10. Do not remove filters.
11. Do not remove joins.
12. Do not remove CTEs.
13. Do not add CTEs.
14. Preserve SELECT expressions.
15. Preserve aggregations.
16. Preserve GROUP BY.
17. Preserve HAVING.
18. Preserve ORDER BY.
19. Preserve window functions.
20. Preserve UNION and UNION ALL.
21. Preserve subqueries.
22. Preserve aliases when represented.
23. Preserve conditions and expressions.
24. Do not simplify the SQL.
25. Do not change the meaning of the SQL.
26. The structure is the source of truth.

Metadata:

Field:
{document.get("field")}

Feature:
{document.get("feature")}

Entity:
{document.get("entity")}

SQL structure:

{json.dumps(
    structure,
    indent=2,
    ensure_ascii=False
)}

Return ONLY the reconstructed SQL.
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    if not response.text:

        raise ValueError(
            "Gemini returned an empty response"
        )

    return response.text.strip()


# ============================================================
# FORMAT SQL
# ============================================================

def format_sql(sql):
    """
    Format SQL and remove unnecessary blank lines.
    """

    try:

        formatted = sqlglot.transpile(
            sql,
            pretty=True
        )[0]

        # Remove blank lines
        lines = formatted.splitlines()

        cleaned_lines = []

        for line in lines:
            if line.strip():
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    except Exception as e:

        print(
            f"    WARNING: sqlglot formatting failed: {e}"
        )

        # Also clean blank lines from unformatted SQL
        lines = sql.splitlines()

        cleaned_lines = [
            line for line in lines
            if line.strip()
        ]

        return "\n".join(cleaned_lines).strip()
    
# MAIN
def main():

    # --------------------------------------------------------
    # Load original SQL index
    # --------------------------------------------------------

    print(
        f"Loading {INPUT_FILE}..."
    )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        sql_index = json.load(f)

    # --------------------------------------------------------
    # Load checkpoint / create output
    # --------------------------------------------------------

    documents = load_documents(
        sql_index
    )

    total = len(documents)

    completed = sum(
        1
        for document in documents
        if document.get("sql")
    )

    remaining = total - completed

    print()
    print("=" * 70)
    print(
        f"Total SQL documents : {total}"
    )
    print(
        f"Already completed   : {completed}"
    )
    print(
        f"Remaining           : {remaining}"
    )
    print("=" * 70)
    print()

    if remaining == 0:

        print(
            "Everything is already completed."
        )

        return

    # --------------------------------------------------------
    # Processing
    # --------------------------------------------------------

    batch_processed = 0
    batch_number = 0

    for index, document in enumerate(documents):

        # ----------------------------------------------------
        # Skip completed SQL
        # ----------------------------------------------------

        if document.get("sql"):

            continue

        print(
            f"[{index + 1}/{total}] "
            f"Field: {document.get('field')} | "
            f"Feature: {document.get('feature')} | "
            f"Entity: {document.get('entity')}"
        )

        try:

            # ------------------------------------------------
            # Gemini
            # ------------------------------------------------

            reconstructed_sql = reconstruct_sql(
                document
            )

            print(
                "    Gemini reconstruction: OK"
            )

            # ------------------------------------------------
            # Format
            # ------------------------------------------------

            formatted_sql = format_sql(
                reconstructed_sql
            )

            print(
                "    SQL formatting: OK"
            )

            # ------------------------------------------------
            # Store
            # ------------------------------------------------

            document["sql"] = formatted_sql

            # ------------------------------------------------
            # IMPORTANT:
            # Save IMMEDIATELY after every successful SQL.
            # ------------------------------------------------

            save_documents(documents)

            print(
                "    Saved checkpoint."
            )

            batch_processed += 1

        except Exception as e:

            print(
                f"    ERROR: {type(e).__name__}: {e}"
            )

            print(
                "    SQL was NOT marked as completed."
            )

            print(
                "    The script will continue."
            )

        # ----------------------------------------------------
        # Small delay
        # ----------------------------------------------------

        time.sleep(
            REQUEST_DELAY
        )

        # ----------------------------------------------------
        # Batch pause
        # ----------------------------------------------------

        if batch_processed >= BATCH_SIZE:

            batch_number += 1

            print()
            print("-" * 70)
            print(
                f"Batch {batch_number} finished."
            )

            print(
                f"Waiting {BATCH_DELAY} seconds..."
            )

            print("-" * 70)
            print()

            time.sleep(
                BATCH_DELAY
            )

            batch_processed = 0

    # --------------------------------------------------------
    # Final statistics
    # --------------------------------------------------------

    completed = sum(
        1
        for document in documents
        if document.get("sql")
    )

    failed = total - completed

    print()
    print("=" * 70)
    print("PROCESSING FINISHED")
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

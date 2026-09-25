import os
import json
import yaml
from pathlib import Path

from google import genai
from dotenv import load_dotenv



# CONFIG
BASE_DIR = Path(__file__).resolve().parent
YAML_FOLDER = BASE_DIR / "yaml_list"
OUTPUT_FILE = BASE_DIR / "terminology_index.json"
MODEL = "gemini-3.5-flash-lite"


# ENVIRONMENT
load_dotenv(BASE_DIR / ".env")
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)


# PROMPT
PROMPT = """
You are a terminology extraction system for a company's
semantic-layer YAML files.

Your task is to extract terminology that a user might use when
asking questions about the features in this YAML.

Extract things such as:

- abbreviations
- acronyms
- internal company terminology
- business terminology
- domain-specific terminology
- product names
- program names
- contract names
- internal codes
- special names
- terminology embedded inside feature names
- terminology embedded inside descriptions
- terminology embedded inside business logic

IMPORTANT RULES:

1. DO NOT omit a term just because you do not understand it.

2. If a term appears to be meaningful terminology but you cannot
   determine its meaning from the provided YAML, return:

   "definition": ""

3. ONLY provide a definition when the YAML itself gives enough
   information to determine the meaning.

4. NEVER invent, guess, or use outside knowledge to define a term.

5. Preserve the original terminology as it appears in the YAML.

6. Do not extract ordinary generic words such as:
   customer, account, date, flag, status, amount, name, id,
   number, type, value, country, etc.

7. If the same terminology appears multiple times in this YAML,
   return it only once.

8. A term can be a single word, abbreviation, acronym, or phrase.

9. Pay special attention to terminology inside:
   - feature name
   - feature description
   - entity
   - field name
   - field description
   - business logic
   - tags
   - domain

10. DO NOT attempt to reconstruct, analyze, or extract terminology
    from SQL. SQL is intentionally excluded.

Return ONLY valid JSON.

Expected format:

[
    {
        "term": "IDK",
        "definition": "I dont Know"
    },
    {
        "term": "ABC",
        "definition": ""
    }
]
"""


# REMOVE SQL

def remove_sql(data):
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():

            # Completely ignore SQL
            if str(key).lower() == "sql":
                continue
            result[key] = remove_sql(value)
        return result

    elif isinstance(data, list):

        return [remove_sql(item)for item in data]
    else:
        return data


# EXTRACT TERMINOLOGY FROM ONE YAML
def extract_terminology(yaml_file):
    """
    Read one YAML file, remove SQL, and ask Gemini
    to extract terminology.
    """

    with open(yaml_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return []

    # Remove SQL BEFORE sending anything to Gemini
    data_without_sql = remove_sql(data)

    yaml_text = yaml.dump(
        data_without_sql,
        allow_unicode=True,
        sort_keys=False
    )

    # Call Gemini
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT + "\n\nYAML:\n" + yaml_text,
        config={
            "temperature": 0
        }
    )

    text = response.text.strip()

    # Handle markdown code fences
    if text.startswith("```"):

        lines = text.splitlines()

        # Remove first line ```json
        lines = lines[1:]

        # Remove final ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    # Parse JSON
    result = json.loads(text)

    if not isinstance(result, list):
        raise ValueError(
            "LLM response is not a list"
        )
    return result


# MAIN
def main():
    # Find YAML files
    yaml_files = list(YAML_FOLDER.glob("*.yaml"))
    yaml_files = sorted(yaml_files)

    terminology_index = {}

    # Process every YAML
    for i, yaml_file in enumerate(yaml_files,1):
        try:
            terms = extract_terminology(yaml_file)
            for item in terms:
                if not isinstance(item, dict):
                    continue

                # Get original term
                original_term = str(item.get("term", "")).strip()

                if not original_term:
                    continue
                # Normalize definition
                term = original_term.lower()
                definition = str(item.get("definition", "")).strip().lower()
                key = term

               
                # New Terminology
                if key not in terminology_index:
                    terminology_index[key] = {
                        "term": term,
                        "definition": definition,
                        "sources": [
                            yaml_file.name
                        ]
                    }

                # Terminology already in index
                else:
                    existing = terminology_index[key]

                    # If we previously didn't know the meaning,
                    # but another YAML provides a definition,
                    # keep the definition.
                    if (not existing["definition"] and definition):
                        existing["definition"] = definition

                    # Add source if not already present
                    if (yaml_file.name not in existing["sources"]):
                        existing["sources"].append(yaml_file.name)

        except Exception as e:
            print(
                f"    ERROR: "
                f"{type(e).__name__}: {e}"
            )

        print()

    # SAVE RESULT
    output = list(terminology_index.values())

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        json.dump(output,f,indent=2,ensure_ascii=False)

    # SUMMARY
    print(f"YAML files processed : {len(yaml_files)}")
    print(f"Unique terminology   : {len(output)}")


# RUN
if __name__ == "__main__":
    main()
from pathlib import Path
import re
import json

TERMINOLOGY_FILE = Path("feature_search/index_dictionary/terminology_index.json")


def load_terminology_index():

    with open(TERMINOLOGY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def expand_terminology(query: str):

    terminology_index = load_terminology_index()

    # Build lookup dictionary
    terminology_map = {}

    for item in terminology_index:

        term = item.get("term", "").strip()
        definition = item.get("definition", "").strip()

        if not term:
            continue

        terminology_map[term.lower()] = {
            "term": term,
            "definition": definition
        }

    # Find terminology in query
    expanded_query = query
    found_terms = []

    
    sorted_terms = sorted(
        terminology_map.keys(),
        key=len,
        reverse=True
    )

    for normalized_term in sorted_terms:

        info = terminology_map[normalized_term]

        original_term = info["term"]
        definition = info["definition"]

        # Find term in user's query
        pattern = re.compile(
            rf"\b{re.escape(normalized_term)}\b",
            re.IGNORECASE
        )

        if not pattern.search(expanded_query):
            continue

        # Terminology found
        found_terms.append({
            "term": original_term,
            "definition": definition
        })

        # If definition is unknown, don't modify the query
        if not definition:
            continue

        replacement = f"{original_term}/{definition}"

        expanded_query = pattern.sub(
            replacement,
            expanded_query
        )

    return {
        "original_query": query,
        "expanded_query": expanded_query,
        "terminology_found": found_terms
    }
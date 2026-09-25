import re
import json
from pathlib import Path
from google import genai
# from ..global_function.cosine_similarity import cosine_similarity
import chromadb

#Load indexing
with open("feature_search/index_dictionary/feature_index.json", "r", encoding="utf-8") as file:
    feature_index = json.load(file)

#Load feature descriptions embeddings
# with open("feature_search/feature_view_embeddings.json","r", encoding="utf-8") as file: 
#     description_embeddings = json.load(file)

BASE_DIR = Path(__file__).resolve().parents[2]

#Load Vector DB
CHROMA_FOLDER = BASE_DIR  / "chromadb"
chroma_client = chromadb.PersistentClient(path=str(CHROMA_FOLDER))
collection = chroma_client.get_collection(name="feature_views_descriptions")

client = genai.Client()


def search_descriptions(query_vector, top_k=3, threshold=0.7):
    results = []

    # for filename, embeddings in description_embeddings.items():
    #     score = cosine_similarity(query_vector,embeddings)
    # if score >= threshold:
    #             results.append((filename, score))
    #  results.sort(key=lambda x: x[1], reverse=True)
    #     return results[:top_k]
    
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k
    )
    matches = []
    ids = results["ids"][0]
    distances = results["distances"][0]
    for filename, distance in zip(ids, distances):
        similarity = 1 - distance
        if similarity >= threshold:
            matches.append((filename, similarity))

    return matches
        

def search_features_by_description(query: str):

    response = client.models.embed_content(model="gemini-embedding-001",contents=query)
    query_vector = response.embeddings[0].values
    matches = search_descriptions(query_vector,top_k=5)

    return [
        {
            "file": filename,
            "score": round(score, 4)
        }
        for filename, score in matches
    ]

def get_features_views_by(value: str, info: str):
    value = value.lower().strip()
    info = info.lower().strip()

    #Users provide entities
    if info == "entity":
        values = re.split(r"\s*(?:,|\bor\b|\band\b)\s*",value)
        values = [v.strip() for v in values if v.strip()]

        results = {}
        
        for entity in values:
            files = feature_index["entity"].get(entity,[])

            results[entity] = files

        return {
            "requested_entities": values,
            "features": results
        }

    elif info == 'description': 
        matches = search_features_by_description(value)

        return {
            "query": value,
            "features": matches 
            }

    #Users provide features_field
    elif info == "field":
        values = re.split(
            r"\s*(?:,|\bor\b|\band\b)\s*",
            value
        )

        values = [v.strip() for v in values if v.strip()]
        results = {}

        for field in values:
            files = feature_index["field_exact"].get(field,[])

            if not files:

                files = feature_index["field_seperated"].get(
                    field,
                    []
                )

            results[field] = files

        return {
            "requested_fields": values,
            "features": results
        }

    #Users give ttl
    elif info == "ttl":

        value = value.replace("of ttl","")
        value = value.replace("ttl","")
        value = value.replace("-year"," year")
        value = value.replace("-years"," years")

        #Find ttl units like 'years' or 'days'
        unit_match = re.search( r"\b(years?|days?|day)\b", value)

        if unit_match:
            unit = unit_match.group(1)
            # Normalize unit
            if unit in ["year","years"]:
                unit = "years"

            elif unit in ["days","day"]:
                unit = "d"

            # Everything before unit
            number_part = value[
                :unit_match.start()
            ]

            # Extract numbers
            numbers = re.findall(r"\d+(?:\.\d+)?", number_part)
            values = [f"{number} {unit}" for number in numbers]

        else:

            # No shared unit
            values = re.split( r"\s*(?:,|\bor\b|\band\b)\s*", value)
            values = [ v.strip() for v in values if v.strip()]

        #Search index
        results = {}

        for ttl in values:
            files = feature_index["ttl"].get(ttl,[])
            results[ttl] = files

        return {
            "requested_ttls": values,
            "features": results
        }

    return f"Unknown information type '{info}'."
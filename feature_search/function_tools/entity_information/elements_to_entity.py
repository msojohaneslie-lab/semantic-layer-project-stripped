
import re
import json
# from ..global_function.cosine_similarity import cosine_similarity
from google import genai
from pathlib import Path
import chromadb
client = genai.Client()

#Load entity embeddings
# with open("feature_search/index_dictionary_unused_index/entities_description_embeddings.json",'r',encoding = 'utf-8') as file:
#     entity_description_business_logic_embeddings = json.load(file)

#Load entity indexing
with open("feature_search/index_dictionary/entities_index.json",'r', encoding = "utf-8") as file:
    entity_index = json.load(file)

#Load Vector DB
BASE_DIR = Path(__file__).resolve().parents[2]
CHROMA_FOLDER = BASE_DIR  / "chromadb"
chroma_client = chromadb.PersistentClient(path=str(CHROMA_FOLDER))
collection = chroma_client.get_collection(name="entities_description_bl_collection")


def search_entity_meanings(query_vector, top_k=3, threshold=0.7):

    results = []

    # for filename, embeddings in entity_description_business_logic_embeddings.items():

    #     score = cosine_similarity(query_vector, embeddings )
    #     if score >= threshold:
    #         results.append((filename, score))
    #         results.sort(key=lambda x: x[1],reverse=True)
        
    # return results[:top_k]

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
        
def search_entities_by_meaning(query: str):
    response = client.models.embed_content(model="gemini-embedding-001", contents=query)
    query_vector = response.embeddings[0].values
    matches = search_entity_meanings(query_vector,top_k=3)

    return [
        {
            "file": filename,
            "score": round(score, 4)
        }
        for filename, score in matches
    ]


def get_entities_by(value: str, info: str):
    value = value.lower().strip()
    info = info.lower().strip()

    #Users provide entities
    if info == "type":

        values = re.split(
            r"\s*(?:,|\bor\b|\band\b)\s*",
            value
        )

        values = [ v.strip() for v in values if v.strip() ]
        results = {}
        
        for types in values:
            files = entity_index["type"].get(types,[])
            results[types] = files

        return {
            "requested_types": values,
            "features": results
        }

    elif info == 'description': 
        matches = search_entities_by_meaning(value)

        return {
            "query": value,
            "entities": matches 
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

            files = entity_index["field_name"].get(field,[])

            if not files:
                files = entity_index["field_name_seperated"].get(field,[])
            results[field] = files

        return {
            "requested_fields": values,
            "features": results
        }

    
    return f"Unknown information type '{info}'."

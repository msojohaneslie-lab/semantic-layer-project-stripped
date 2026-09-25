import re
import json
from google import genai
from pathlib import Path
import chromadb
# from ..global_function.cosine_similarity import cosine_similarity


#Load field descriptions and business logic embeddings
# with open("feature_search/field_embeddings.json",'r',encoding="utf-8") as file:
    # feature_field_description_business_logic_embeddings = json.load(file)

BASE_DIR = Path(__file__).resolve().parents[2]
CHROMA_FOLDER = BASE_DIR  / "chromadb"
chroma_client = chromadb.PersistentClient(path=str(CHROMA_FOLDER))
collection = chroma_client.get_collection(name="feature_description_bl_collection")

client = genai.Client()

def search_field_meanings(query_vector, top_k=3, threshold=0.7):
    results = []

    # for key, field_data in feature_field_description_business_logic_embeddings.items():
    #     score = cosine_similarity(query_vector,field_data["embedding"])
    #     if score >= threshold:
    #         results.append(
    #             (
    #                 field_data["feature_name"],
    #                 field_data["field_name"],
    #                 score
    #             )
    #         )

    # # Highest similarity first
    # results.sort(key=lambda x: x[2], reverse=True)

    # # Return maximum 3
    # return results[:top_k]
    results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["metadatas", "distances"]
        )
    matches = []
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    for metadata, distance in zip(metadatas, distances):
        similarity = 1 - distance
        if similarity >= threshold:
            matches.append({
                "feature": metadata["feature_view"],
                "field": metadata["field_name"],
                "entity": metadata["entity"],
                "yaml_file": metadata["yaml_file"],
                "business_logic": metadata["business_logic"],
                "score": round(similarity, 4)
            })
    
    return matches


def search_features_by_field_meaning(query: str):

    response = client.models.embed_content(model="gemini-embedding-001", contents=query)
    query_vector = response.embeddings[0].values

    matches = search_field_meanings(query_vector,top_k=3,threshold=0.7)

    return matches

def get_feature_fields_by(value: str, info: str):
    if info not in ["description", "business_logic"]:

        return {
            "results": {},
            "info": info,
            "not_found": [value],
            "error": f"Unknown information type '{info}'."
        }

    values = re.split(r"\s*(?:,|\bor\b|\band\b)\s*",value)

    values = [v.strip() for v in values if v.strip()]

    results = {}
    not_found = []

    for search_value in values:
        matches = search_features_by_field_meaning(search_value)

        if matches:
            results[search_value] = matches

        else:
            not_found.append(search_value)

    return {
        "results": results,
        "info": info,
        "not_found": not_found
    }
from feature_search.SQL_parser.embed_sql import normalize_sql
from google import genai
import json
import yaml
from ..global_function.cosine_similarity import cosine_similarity
from google.genai import types


client = genai.Client()

with open("feature_search/SQL_parser/sql_embeddings.json", "r", encoding="utf-8") as file:
    sql_embeddings = json.load(file)

def search_sql_embeddings(query_vector,top_k=5,threshold=0.70):
  
    results = []

    for sql_data in sql_embeddings:

        embedding = sql_data.get("embedding")

        if not embedding:
            continue

        score = cosine_similarity(query_vector, embedding)

        if score >= threshold:

            results.append({
                "field": sql_data.get("field", ""),
                "entity": sql_data.get("entity", ""),
                "score": round(float(score), 4)
            })

    # Highest similarity first
    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return results[:top_k]


def get_features_fields_by_sql(value: str):
    
    value = normalize_sql(value)

    if not value:
        return {
            "query": value,
            "status": "no_match",
            "features": []
        }
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=value,
        config=types.EmbedContentConfig(
        task_type="SEMANTIC_SIMILARITY",
        output_dimensionality=3072
)
    )

    query_vector = response.embeddings[0].values
    matches = search_sql_embeddings(query_vector, top_k=5,threshold=0.70)

    return {
        "query": value,
        "status": "match_found" if matches else "no_match",
        "features": matches
    }
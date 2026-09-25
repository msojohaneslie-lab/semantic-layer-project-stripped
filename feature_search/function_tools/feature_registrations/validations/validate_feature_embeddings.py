from google import genai
# from ...global_function.cosine_similarity import cosine_similarity
from ...global_function.read_json import load_json_file
from ...feature_registrations.validations.validate_entity import get_entity_feature_views
from pathlib import Path
import chromadb
import os
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key= api_key)
EMBEDDING_MODEL = "gemini-embedding-001"

#Load ChromaDB
CHROMA_FOLDER = BASE_DIR / "chromadb"
chroma_client = chromadb.PersistentClient(path=str(CHROMA_FOLDER))
field_collection = chroma_client.get_collection(name="feature_description_bl_collection")
feature_view_collection = chroma_client.get_collection(name="feature_views_descriptions")

FEATURE_DUPLICATE_THRESHOLD = 0.8
MAX_FEATURE_VIEW_CANDIDATES = 3
FEATURE_VIEW_SIMILARITY_THRESHOLD = 0.01
# FEATURE_SEMANTIC_INDEX_FILE = (BASE_DIR / "feature_semantic_index.json")
# FEATURE_VIEW_SEMANTIC_INDEX_FILE = (BASE_DIR /"index_dictionary"/"unused_index"/"feature_view_embeddings_entity_based.json")

def generate_embedding(description: str, business_logic: str):
    text = (
        f"Description: {description}\n"
        f"Business Logic: {business_logic}"
    )

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )

    return response.embeddings[0].values

def get_feature_embedding(description, business_logic):
    return generate_embedding(
        description=description,
        business_logic=business_logic
    )


def check_semantic_duplicate(
    new_embedding,
    field_name: str,
    field_type: str,
    description: str,
    business_logic: str,
    entity: str,
    sql: str,
    flag: bool,
):

    if flag is not True:
        return {
            "status": "valid",
            "message": "Semantic duplicate checking is disabled.",
        }

    try:
        results = field_collection.query(
            query_embeddings=[new_embedding],
            n_results=5,
            where={
                "entity": entity
            },
            include=[
                "metadatas",
                "distances"
            ]
        )

    except Exception as e:
        return {
            "status": "error",
            "message": (
                "Failed to search feature-field "
                f"semantic collection: {str(e)}"
            ),
        }

    ids = results["ids"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    if not ids:
        return {
            "status": "valid",
            "similarity": None,
            "message": (
                "No existing feature field was found "
                "for semantic comparison."
            ),
        }

    # Since the collection uses cosine distance:
    # similarity = 1 - distance
    for metadata, distance in zip(metadatas, distances):
        similarity = 1 - distance
        if similarity >= FEATURE_DUPLICATE_THRESHOLD:

            return {
                "status": "duplicate_warning",
                "match_type": "semantic",
                "similarity": similarity,

                "existing_feature": metadata.get("feature_view"),
                "existing_field": metadata.get("field_name"),
                "existing_feature_view": metadata.get("feature_view"),
                "existing_yaml_file": metadata.get("yaml_file"),
                "entity": metadata.get("entity"),
                "message": (
                    "The new feature field is "
                    "semantically similar to the "
                    f"existing field "
                    f"'{metadata.get('field_name')}' "
                    f"in feature view "
                    f"'{metadata.get('feature_view')}' "
                    f"(similarity: {similarity:.3f})."
                ),

                "requires_confirmation": True,
            }

    return {
        "status": "valid",
        "similarity": None,
        "message": (
            "No semantic duplicate was detected."
        ),
        "field_name": field_name,
        "field_type": field_type,
        "description": description,
        "business_logic": business_logic,
        "entity": entity,
        "sql": sql,
    }

def find_similar_feature_views(new_embedding,entity,):
    try:
        results = feature_view_collection.query(
            query_embeddings=[new_embedding],
            n_results=MAX_FEATURE_VIEW_CANDIDATES,
            where={
                "entity": entity
            },
            include=[
                "metadatas",
                "distances"
            ]
        )

    except Exception as e:

        return {
            "status": "error",
            "message": (
                "Failed to search feature-view "
                f"semantic collection: {str(e)}"
            ),
        }

    ids = results["ids"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    candidates = []

    for metadata, distance in zip(metadatas,distances):
        similarity = 1 - distance
        if similarity >= FEATURE_VIEW_SIMILARITY_THRESHOLD:
            candidates.append({
                "file": metadata.get("yaml_file"),
                "feature_view": metadata.get(
                    "feature_view"
                ),
                "entity": metadata.get(
                    "entity"
                ),
                "similarity": similarity,
            })

    if candidates:
        return {
            "status": "candidates_found",
            "candidates": candidates,
            "checked_yaml_count": None,
            "threshold": FEATURE_VIEW_SIMILARITY_THRESHOLD,
            "message": (
                f"Found {len(candidates)} "
                "similar feature-view candidate(s)."
            ),
        }

    return {
        "status": "no_candidates",
        "candidates": [],
        "checked_yaml_count": None,
        "threshold": FEATURE_VIEW_SIMILARITY_THRESHOLD,
        "message": (
            "No existing feature view passed "
            "the similarity threshold."
        ),
    }


def validate_semantic_and_find_feature_views(field_name: str,field_type: str,description: str,business_logic: str,entity: str,sql: str, flag: bool):
    embedding = get_feature_embedding(description,business_logic)
    duplicate_result = check_semantic_duplicate(embedding,field_name,field_type,description,business_logic,entity,sql, flag)
    feature_views = get_entity_feature_views(entity)

    if not feature_views:
        return {
            "status": "valid",
            "duplicate": duplicate_result,
            "candidates": [],
            "field_name": field_name,
            "field_type": field_type,
            "description": description,
            "business_logic": business_logic,
            "entity": entity,
            "sql": sql,
        }

    feature_view_result = find_similar_feature_views(embedding,entity)

    return {
        "status": "valid",
        "duplicate": duplicate_result,
        "candidates": feature_view_result,
        "field_name": field_name,
        "field_type": field_type,
        "description": description,
        "business_logic": business_logic,
        "entity": entity,
        "sql": sql,
    }
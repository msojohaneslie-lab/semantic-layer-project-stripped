from pathlib import Path
from google import genai
import os
from dotenv import load_dotenv
import json
import yaml


BASE_DIR = Path(__file__).resolve().parents[2]



BASE_DIR = Path(__file__).parent.parent

load_dotenv(BASE_DIR / ".env")
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

YAML_FOLDER = BASE_DIR / "yaml_list"


def make_embedding_structure(data):
    text = []

    text.append(f"name: {data.get('name', '')}")
    text.append(f"description: {data.get('description', '')}")

    return "\n".join(text)


def generate_embeddings():

    output_file = (BASE_DIR/"index_dictionary"/"feature_view_embeddings_entity_based.json")
    print("BASE_DIR:", BASE_DIR)
    print("YAML_FOLDER:", YAML_FOLDER)
    print("YAML_FOLDER EXISTS:", YAML_FOLDER.exists())


    # Load existing embeddings if available
    if output_file.exists():
        with open(output_file,"r",encoding="utf-8") as file: 
            embeddings = json.load(file)

    else:
        embeddings = {}

    # Loop through YAML files
    for yaml_file in YAML_FOLDER.glob("*.yaml"):
        filename = yaml_file.name

        # Read YAML
        with open(
            yaml_file,
            "r",
            encoding="utf-8"
        ) as file:
            yaml_data = yaml.safe_load(file)

        # Get entity
        entity = yaml_data.get("entity")

        if not entity:
            continue

        # Normalize entity
        entity = entity.lower().strip()

        # Create entity dictionary if needed
        if entity not in embeddings:
            embeddings[entity] = {}

        # Skip if embedding already exists
        if filename in embeddings[entity]:
            continue

        # Create text for embedding
        text = make_embedding_structure(yaml_data)

        print(
            f"Generating embedding: "
            f"entity={entity}, file={filename}"
        )

        # Generate embedding
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text
        )

        vector = result.embeddings[0].values

        # Store
        embeddings[entity][filename] = vector

        # Save after every embedding
        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                embeddings,
                file,
                ensure_ascii=False
            )

    print("Embedding generation completed.")


if __name__ == "__main__":
    generate_embeddings()
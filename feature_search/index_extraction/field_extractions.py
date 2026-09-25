import json
from pathlib import Path

import yaml


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

YAML_FOLDER = BASE_DIR / "yaml_list"
OUTPUT_FILE = BASE_DIR / "field_index.json"


# ============================================================
# BUILD FIELD INDEX
# ============================================================

def build_field_index():
    field_index = {}

    yaml_files = list(YAML_FOLDER.rglob("*.yaml")) + list(
        YAML_FOLDER.rglob("*.yml")
    )

    print(f"Found {len(yaml_files)} YAML files.")

    processed_files = 0
    skipped_files = 0
    processed_fields = 0

    for yaml_file in yaml_files:

        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

        except Exception as e:
            print(f"[ERROR] Failed to read {yaml_file}: {e}")
            skipped_files += 1
            continue

        # ----------------------------------------------------
        # Feature name
        # ----------------------------------------------------

        feature_name = data.get("name")

        if not feature_name:
            print(f"[SKIP] No feature name: {yaml_file}")
            skipped_files += 1
            continue

        # ----------------------------------------------------
        # Entity
        # ----------------------------------------------------

        entity = data.get("entity")

        # ----------------------------------------------------
        # Feature fields
        # ----------------------------------------------------

        feature_fields = data.get("feature_fields", [])

        if not isinstance(feature_fields, list):
            print(
                f"[SKIP] feature_fields is not a list: "
                f"{yaml_file}"
            )
            skipped_files += 1
            continue

        # ----------------------------------------------------
        # Relative file path
        # ----------------------------------------------------

        try:
            relative_file = str(
                yaml_file.relative_to(BASE_DIR)
            )
        except ValueError:
            relative_file = str(yaml_file)

        # ----------------------------------------------------
        # Process fields
        # ----------------------------------------------------

        for field in feature_fields:

            if not isinstance(field, dict):
                continue

            field_name = field.get("name")

            if not field_name:
                continue

            field_entry = {
                "feature": feature_name,
                "entity": entity,
                "type": field.get("type"),
                "description": field.get("description"),
                "business_logic": field.get("business_logic"),
                "file": yaml_file.name,
            }

            # ------------------------------------------------
            # Add field
            # ------------------------------------------------

            if field_name not in field_index:
                field_index[field_name] = []

            field_index[field_name].append(field_entry)

            processed_fields += 1

        processed_files += 1

    # ========================================================
    # SAVE INDEX
    # ========================================================

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            field_index,
            f,
            indent=2,
            ensure_ascii=False
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    unique_fields = len(field_index)

    print()
    print("=" * 60)
    print("FIELD INDEX COMPLETE")
    print("=" * 60)
    print(f"YAML files found      : {len(yaml_files)}")
    print(f"YAML files processed  : {processed_files}")
    print(f"YAML files skipped    : {skipped_files}")
    print(f"Fields processed      : {processed_fields}")
    print(f"Unique fields         : {unique_fields}")
    print(f"Output                : {OUTPUT_FILE}")
    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    build_field_index()
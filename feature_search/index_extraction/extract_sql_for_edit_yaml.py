import json
from pathlib import Path
import yaml
import sqlglot
from sqlglot import exp
from ..SQL_parser.query_structure_extract import extract_structure


BASE_DIR = Path(__file__).resolve().parents[1]
# .parent

YAML_FOLDER = BASE_DIR / "yaml_list"
OUTPUT_FILE = (BASE_DIR/ "index_dictionary"/ "feature_view_sql_structure_index.json")


DIALECT = "maxcompute"


def normalize_name(value):
    if value is None:
        return None

    return str(value).strip().lower()


def extract_sql_index(sql):

    tree = sqlglot.parse_one(
        sql,
        dialect=DIALECT
    )

    # Find all CTEs
    cte_map = {}

    for cte in tree.find_all(exp.CTE):

        cte_name = normalize_name(
            cte.alias
        )

        cte_map[cte_name] = cte.this

    # Result
    result = {
        "ctes": {},
        "final": None
    }

    # --------------------------------------------------
    # Extract every CTE
    # --------------------------------------------------

    for cte_name, cte_query in cte_map.items():

        # CTE.this is normally a Subquery
        if isinstance(
            cte_query,
            exp.Subquery
        ):
            cte_query = cte_query.this

        result["ctes"][cte_name] = (
            extract_structure(
                cte_query,
                cte_map
            )
        )

    # --------------------------------------------------
    # Extract final SELECT
    # --------------------------------------------------

    if isinstance(
        tree,
        (exp.Select, exp.Union)
    ):

        result["final"] = extract_structure(
            tree,
            cte_map
        )

    return result

def generate_index():

    index = {}

    yaml_files = list(
        YAML_FOLDER.glob("*.yaml")
    )

    print(
        f"Found {len(yaml_files)} YAML files"
    )

    for yaml_path in yaml_files:

        print(
            f"Processing: {yaml_path.name}"
        )

        # ----------------------------------------------
        # Read YAML
        # ----------------------------------------------

        try:

            with open(
                yaml_path,
                "r",
                encoding="utf-8"
            ) as file:

                data = yaml.safe_load(file)

        except Exception as e:

            print(
                f"  YAML ERROR: {e}"
            )

            continue

        if not isinstance(
            data,
            dict
        ):

            print(
                "  Skipped: invalid YAML structure"
            )

            continue

        # ----------------------------------------------
        # Get SQL
        # ----------------------------------------------

        sql = data.get("sql")

        if not sql:

            print(
                "  Skipped: no SQL"
            )

            continue

        # ----------------------------------------------
        # Parse SQL
        # ----------------------------------------------

        try:

            structure = extract_sql_index(
                sql
            )

        except Exception as e:

            print(
                f"  SQL PARSE ERROR: {e}"
            )

            continue

        # ----------------------------------------------
        # Store
        # ----------------------------------------------

        index[yaml_path.name] = {
            "entity": normalize_name(
                data.get("entity")
            ),
            "ctes": structure["ctes"],
            "final": structure["final"]
        }

        print(
            f"  CTEs found: "
            f"{len(structure['ctes'])}"
        )

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            index,
            file,
            indent=2,
            ensure_ascii=False
        )

    print()
    print(
        "======================================"
    )
    print(
        "INDEX CREATED"
    )
    print(
        f"YAML files: {len(index)}"
    )
    print(
        f"Output: {OUTPUT_FILE}"
    )
    print(
        "======================================"
    )


if __name__ == "__main__":
    generate_index()
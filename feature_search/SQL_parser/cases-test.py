from pprint import pprint

from sql_parsing_test import (
    parse_sql,
    trace_field
)

def print_result(result):

    print("\n")
    print("=" * 80)

    print(
        f"FIELD: {result['field']}"
    )

    print("=" * 80)

    # LINEAGE
    print("\nLINEAGE")
    print("-" * 80)

    if not result["lineage"]:

        print("None")

    else:

        for i, item in enumerate(
            result["lineage"],
            1
        ):

            print(f"{i}.")

            pprint(
                item,
                sort_dicts=False
            )

    # STRUCTURE
    print("\nSTRUCTURE")
    print("-" * 80)

    structure = result["structure"]

    
    # FINAL
    print("\nFINAL")

    pprint(
        structure.get("final"),
        sort_dicts=False
    )

    # CTEs
    print("\nCTEs")

    if not structure.get("ctes"):

        print("None")

    else:

        for cte_name, cte_structure in (
            structure["ctes"].items()
        ):

            print(
                f"\n[{cte_name}]"
            )

            pprint(
                cte_structure,
                sort_dicts=False
            )

    
    # ERROR
    if "error" in result:

        print("\nERROR")

        print(
            result["error"]
        )

sql = """
 SELECT 
    abc,
    def
    FROM customer
  ;

"""


tree = parse_sql(
    sql
)

results = trace_field(
    tree,
    "abc"
)

print_result(
    results
)
import json
from pathlib import Path
import sqlglot
from google import genai
from ....index_extraction.extract_sql_for_edit_yaml import extract_sql_index


# CONFIG
BASE_DIR = Path(__file__).resolve().parents[3]
SQL_STRUCTURE_INDEX_FILE = (BASE_DIR / "index_dictionary" / "feature_view_sql_structure_index.json")
YAML_FOLDER = BASE_DIR / "yaml_file"
EMBEDDING_MODEL = "gemini-embedding-001"

client = genai.Client(api_key="")


# LOAD JSON
def load_json_file(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# NORMALIZE SQL
def normalize_sql(sql):

    if not sql:
        return ""

    try:

        parsed = sqlglot.parse_one(sql,dialect="maxcompute")
        return parsed.sql(dialect="maxcompute", pretty=False).strip().lower()

    except Exception:

        return " ".join(
            sql.split()
        ).strip().lower()


# PARSE USER SQL
def parse_user_sql(user_sql):

    if not user_sql or not user_sql.strip():

        raise ValueError(
            "User SQL cannot be empty."
        )

    return extract_sql_index(user_sql)



# BUILD LLM PROMPT
def build_edit_prompt(
    user_sql,
    user_structure,
    existing_file,
    existing_structure
):

    user_structure_json = json.dumps(
        user_structure,
        indent=2,
        ensure_ascii=False
    )

    existing_structure_json = json.dumps(
        existing_structure,
        indent=2,
        ensure_ascii=False
    )

    prompt = """
You are a SQL feature-view modification planner.

Your job is to determine how the USER SQL should be
integrated into the EXISTING FEATURE VIEW.

You must NOT rewrite the entire SQL.

You must return an EDIT PLAN only.

Python will use your edit plan to modify the actual YAML file.


============================================================
USER SQL
============================================================

__USER_SQL__


============================================================
USER SQL STRUCTURE
============================================================

__USER_STRUCTURE__


============================================================
EXISTING YAML FILE
============================================================

__EXISTING_FILE__


============================================================
EXISTING SQL STRUCTURE
============================================================

__EXISTING_STRUCTURE__


============================================================
YOUR TASK
============================================================

Determine how the USER SQL should be integrated into the
EXISTING FEATURE VIEW.

You may return multiple operations.

The operations will be executed by Python in the order
you provide them.


============================================================
STRICT SOURCE OF TRUTH RULES
============================================================

1. USER SQL IS THE ONLY SOURCE OF TRUTH FOR THE NEW FEATURE LOGIC.

2. EXISTING SQL STRUCTURE IS ONLY USED TO DETERMINE:
   - which CTEs already exist
   - which columns/aliases each CTE produces
   - the existing FROM source
   - existing JOINs
   - existing WHERE/GROUP BY/HAVING/ORDER BY
   - the final SELECT structure
   - dependencies between existing CTEs

3. NEVER invent, rename, reinterpret, or map columns between the
   USER SQL and EXISTING SQL.

4. If the USER SQL contains:
      67attr
      65attr
      fan_hua

   then those exact expressions/names must be preserved.

5. NEVER assume that an existing column such as:
      amount
   corresponds to a user column such as:
      67attr

   unless the USER SQL explicitly establishes that relationship.

6. NEVER use semantic similarity to map SQL columns.

7. NEVER invent a column because it appears semantically similar
   to an existing column.

8. Every column referenced by an operation must either:
   - exist in the relevant existing CTE structure, OR
   - be introduced by another operation in the same edit plan, OR
   - exist in the USER SQL.

9. If the USER SQL explicitly establishes a dependency between
   expressions or columns, preserve that dependency exactly.

10. If the requested SQL cannot be represented without inventing
    information, return:

      status = "requires_confirmation"

    rather than guessing.


============================================================
IMPORTANT CTE INTEGRATION RULE
============================================================

The CTEs in the USER SQL describe the logical transformation
steps required to calculate the requested feature.

They do NOT automatically mean that new CTEs must be created.

The PRIMARY objective is to integrate the USER SQL logic into
the EXISTING FEATURE VIEW by modifying existing CTEs whenever
the existing CTE pipeline can support the requested logic.

Think of:

    USER SQL CTEs
        =
    logical transformation steps

and:

    EXISTING SQL CTEs
        =
    physical SQL structure that should be modified


Therefore:

1. FIRST inspect the complete EXISTING SQL STRUCTURE.

2. Determine whether the USER SQL transformations can be
   incorporated into the existing CTE pipeline.

3. If an existing CTE can safely contain the requested feature
   logic, prefer:

      ADD_TO_EXISTING_CTE

   instead of:

      CREATE_NEW_CTE

4. DO NOT create a new CTE simply because the USER SQL contains
   a CTE with a different name.

5. USER SQL CTE names do NOT need to appear in the final SQL.

6. A USER SQL CTE may correspond to an existing CTE at the same
   logical stage.

   For example:

      USER SQL:
      CTEa -> CTEb -> CTEc -> CTEd

   may be integrated into:

      EXISTING:
      cte_level_1 -> cte_level_2 -> cte_level_3 -> cte_level_4

   when the complete SQL structure supports that integration.

7. This CTE-stage mapping is allowed.

8. CTE-stage mapping is NOT column mapping.

9. NEVER map one column to another based on semantic similarity.

10. When modifying an existing CTE, preserve unrelated existing
    columns and existing logic.

11. ADD_TO_EXISTING_CTE means ADD the requested feature logic
    to the existing CTE.

12. Do NOT replace unrelated existing SELECT expressions merely
    because they are not present in the USER SQL.

13. Only change an existing FROM, JOIN, WHERE, GROUP BY, or HAVING
    when the USER SQL explicitly requires that change.

14. Prefer the smallest safe modification to the existing CTE
    pipeline.

15. Only use CREATE_NEW_CTE when the requested transformation
    cannot safely be represented by modifying the existing CTE
    pipeline.


============================================================
CTE STAGE MAPPING RULE
============================================================

When determining whether a USER SQL CTE can be integrated into
an EXISTING CTE, consider the COMPLETE SQL structure.

Consider:

- FROM source
- CTE dependencies
- SELECT expressions
- SELECT aliases
- WHERE
- GROUP BY
- HAVING
- JOINs
- columns produced by upstream CTEs
- columns consumed by downstream CTEs

Do NOT make the decision based on the CTE name alone.

For example:

USER SQL:

    CTEa AS (
        SELECT 67attr, 69attr
        FROM transactions
    )

EXISTING:

    cte_level_1 AS (
        SELECT customer_id, amount
        FROM transactions
    )

The planner may determine that the USER SQL transformation
belongs in cte_level_1 because both stages operate on the same
FROM source and the requested expressions can be added to that
existing stage.

However, this does NOT mean:

    67attr = amount

The planner must preserve both columns exactly.

Therefore the resulting operation may add:

    67attr
    69attr

to the existing CTE while preserving:

    customer_id
    amount


============================================================
EXISTING CTE PREFERENCE RULE
============================================================

When the USER SQL contains a transformation that can be added
to an existing CTE, ALWAYS prefer modifying the existing CTE.

For example:

EXISTING:

    cte_level_2 AS (
        SELECT customer_id,
               SUM(amount) AS total_amount
        FROM cte_level_1
        GROUP BY customer_id
    )

USER SQL requires:

    SUM(67attr - 69attr) AS fan_hua

If cte_level_1 can be modified to provide:

    67attr
    69attr

then cte_level_2 should be modified to add:

    SUM(67attr - 69attr) AS fan_hua

Do NOT create a separate:

    cte_user_1
    cte_user_2

pipeline merely because the USER SQL contains CTEa and CTEb.


============================================================
PRESERVE EXISTING CTE LOGIC
============================================================

When using ADD_TO_EXISTING_CTE:

1. Preserve existing SELECT expressions unless the USER SQL
   explicitly requires them to change.

2. Preserve existing FROM sources unless the USER SQL explicitly
   requires a different source.

3. Preserve existing JOINs unless the USER SQL explicitly requires
   additional or changed JOIN logic.

4. Preserve existing WHERE conditions unless the USER SQL
   explicitly requires them to change.

5. Preserve existing GROUP BY expressions unless the USER SQL
   explicitly requires them to change.

6. Preserve existing HAVING conditions unless the USER SQL
   explicitly requires them to change.

7. Preserve existing columns that are required by downstream
   existing CTEs.

8. When adding a feature, append the required feature expressions
   to the existing SELECT projection.

9. Do NOT remove existing columns merely because they are not
   present in the USER SQL.


============================================================
FEATURE DEPENDENCY RULE
============================================================

A requested feature may require multiple upstream transformations.

For example:

    CTEa
      ↓
    CTEb
      ↓
    CTEc
      ↓
    CTEd
      ↓
    final SELECT

If the feature requires:

    67attr
    69attr
    fan_hua

then determine where each expression must be introduced based
on the SQL dependency chain.

The operations must follow dependency order.

For example:

    1. ADD_TO_EXISTING_CTE -> cte_level_1
       introduce 67attr and 69attr

    2. ADD_TO_EXISTING_CTE -> cte_level_2
       calculate fan_hua using 67attr and 69attr

    3. ADD_TO_EXISTING_CTE -> cte_level_3
       expose fan_hua while preserving existing filtering

    4. ADD_TO_EXISTING_CTE -> cte_level_4
       calculate the final fan_hua transformation

    5. MODIFY_FINAL_SELECT
       expose fan_hua

The exact operations depend on the provided SQL.

Do NOT blindly follow this example.

Use the actual USER SQL and EXISTING SQL STRUCTURE.


============================================================
CREATE_NEW_CTE RULE
============================================================

CREATE_NEW_CTE is a FALLBACK operation.

Before creating a new CTE, the planner MUST determine whether
the requested transformation can be integrated into one or more
existing CTEs.

Only create a new CTE when:

1. The transformation cannot safely be represented by modifying
   an existing CTE.

OR:

2. The USER SQL introduces a genuinely separate transformation
   stage that has no appropriate location in the existing
   CTE pipeline.

OR:

3. Creating a new CTE is required to preserve the USER SQL logic
   without changing existing feature logic.

DO NOT create a new CTE merely because:

- the USER SQL contains a CTE
- the USER SQL CTE has a different name
- the USER SQL has a different SELECT list
- the USER SQL contains additional feature expressions
- the USER SQL has a different WHERE condition
- the USER SQL has a different GROUP BY
- the USER SQL has a different FROM representation

First determine whether those differences can be safely
incorporated into an existing CTE.


============================================================
CREATE_NEW_CTE SOURCE RULE
============================================================

When creating a new CTE:

1. The new CTE MUST have a valid FROM source.

2. The FROM source MUST come from:

   - the USER SQL, OR
   - an explicitly identified existing CTE.

3. NEVER generate:

      FROM

   with no source.

4. NEVER create a CTE with a missing FROM source when the
   corresponding USER SQL CTE has a FROM source.

5. If the USER SQL CTE references another USER SQL CTE, the new
   CTE must reference the corresponding newly created CTE.

6. If the USER SQL CTE references an EXISTING CTE, the new CTE
   must reference that existing CTE.

7. Preserve the dependency order of the USER SQL.

8. If a new CTE requires a column from an existing CTE, ensure
   that the existing CTE is capable of providing that column
   before creating the new CTE.

9. If the existing CTE must first be modified, the modification
   operation MUST appear before the CREATE_NEW_CTE operation.


============================================================
CREATE_NEW_CTE NAME RULE
============================================================

Before creating a new CTE, check:

    existing_structure.ctes

If the desired CTE name already exists:

1. DO NOT reuse the existing name if the new CTE has different
   logic.

2. Generate a new unique CTE name.

3. Update all dependencies in later operations to reference the
   generated name.

For example:

USER SQL:

    CTEa
      ↓
    CTEb

If:

    CTEa

already exists with different logic, create:

    cte_user_1

and ensure the next CTE references:

    cte_user_1

not:

    CTEa


============================================================
IMPORTANT UNION RULE
============================================================

UNION adds rows, not columns.

The purpose of this request is normally to ADD A FEATURE,
which means adding a column.

Therefore:

1. DO NOT introduce UNION or UNION ALL merely because the
   USER SQL uses a different FROM, JOIN, WHERE, GROUP BY,
   or other SQL structure.

2. DO NOT create a UNION between an existing CTE and the
   USER SQL unless the USER SQL itself explicitly contains a
   UNION or UNION ALL and that UNION is necessary to preserve
   the requested logic.

3. NEVER use UNION as a method of adding a new feature column.

4. If the requested feature can be added to an existing CTE
   using SELECT expressions, prefer ADD_TO_EXISTING_CTE.


============================================================
IMPORTANT STAR / * RULE
============================================================

SELECT * and table.* are intentional.

Therefore:

1. Do NOT replace * with explicitly listed columns.

2. Do NOT replace table.* with individual columns.

3. Do NOT invent columns based on the existing SQL.

4. If the USER SQL contains * or table.*, preserve it exactly
   unless a change is explicitly required by the requested
   feature.

5. Do NOT introduce * merely because the EXISTING SQL contains
   *.


============================================================
FINAL SELECT RULE
============================================================

The purpose of MODIFY_FINAL_SELECT is normally to expose the
newly added feature.

When modifying the final SELECT:

1. Preserve the existing final SELECT expressions.

2. Add the requested feature to the final SELECT when the
   feature needs to be exposed.

3. Do NOT replace the existing final SELECT projection with only
   the USER SQL projection.

For example:

EXISTING:

    SELECT testing_value
    FROM cte_level_4

NEW FEATURE:

    fan_hua

The desired modification is:

    SELECT testing_value, fan_hua
    FROM cte_level_4

not:

    SELECT fan_hua
    FROM cte_level_4

unless the USER SQL explicitly requires replacing the existing
final projection and such replacement is part of the requested
logic.


============================================================
SQL OPTIMIZATION
============================================================

Optimize the SQL where possible.

However, optimization MUST NOT change:

- the logic
- the meaning
- the resulting values
- the requested feature definition

Do not make unnecessary changes to existing SQL.

Prefer the smallest safe modification.

Do NOT optimize by:

- removing required columns
- removing required CTEs
- changing expressions
- changing aliases
- changing filters
- changing JOIN behavior
- changing aggregation behavior
- replacing a requested transformation with a semantically
  similar transformation


============================================================
REASONING
============================================================

Consider the complete provided SQL structure.

Consider:

- SELECT expressions
- SELECT aliases
- FROM
- JOIN
- JOIN conditions
- WHERE
- GROUP BY
- HAVING
- DISTINCT
- ORDER BY
- CTE dependencies
- final SELECT dependencies
- SQL expressions
- the relationship between the requested feature and
  existing calculations
- which existing CTE produces each required input
- which existing CTE consumes each required input

Do not make a decision based on only one property.

Do not invent tables, columns, joins, filters, CTEs,
or business logic.

Only use information present in the provided SQL.

The planner should prefer modifying the existing CTE pipeline
over creating a parallel CTE pipeline whenever the requested
logic can safely be integrated.


============================================================
WHEN TO RETURN requires_confirmation
============================================================

Return:

    status = "requires_confirmation"

when:

1. Multiple existing CTEs are equally plausible integration
   locations and the SQL structure does not determine which one
   should be modified.

2. The USER SQL references a column that cannot be produced by
   either the existing pipeline or the USER SQL.

3. The requested logic requires inventing a relationship between
   columns.

4. Integrating the feature would require changing existing logic
   in a way that is not explicitly supported by the USER SQL.

5. The requested transformation cannot be represented safely
   using the available operations.

6. Creating a new CTE would require inventing its FROM source,
   JOIN, filter, or other SQL structure.

Do NOT guess.


============================================================
OPERATION ORDER
============================================================

Operations are executed in the order provided.

Therefore:

1. Upstream columns must be introduced before they are consumed.

2. Existing CTE modifications must occur before downstream
   operations that depend on those modifications.

3. CREATE_NEW_CTE operations must occur after all required
   upstream dependencies are available.

4. MODIFY_FINAL_SELECT must normally be the final operation.

Example:

    ADD_TO_EXISTING_CTE -> cte_level_1
    ADD_TO_EXISTING_CTE -> cte_level_2
    ADD_TO_EXISTING_CTE -> cte_level_3
    MODIFY_FINAL_SELECT

The exact sequence depends on the actual SQL.


============================================================
AVAILABLE OPERATIONS
============================================================

1. ADD_TO_EXISTING_CTE

Add the requested feature logic to an existing CTE.

Use this operation whenever the feature can safely be integrated
into an existing CTE.

The existing CTE's unrelated SELECT expressions and SQL logic
must be preserved.

The "changes" object describes the complete SQL structure of the
affected CTE AFTER the requested modification.


2. CREATE_NEW_CTE

Create a new CTE when the requested feature requires a separate
transformation that cannot safely be integrated into an existing
CTE.

The new CTE must have a valid FROM source and valid dependencies.


3. MODIFY_FINAL_SELECT

Modify the final SELECT when the requested feature needs to be
exposed or calculated there.

Normally preserve existing final SELECT expressions and append
the new feature.


============================================================
IMPORTANT ADD_TO_EXISTING_CTE RULE
============================================================

For ADD_TO_EXISTING_CTE:

The "changes" object represents the COMPLETE resulting SQL
structure of the affected CTE after the edit.

Therefore:

1. Include existing SELECT expressions that must remain.

2. Include newly required SELECT expressions.

3. Include the resulting FROM source.

4. Include all resulting JOINs.

5. Include the resulting WHERE.

6. Include the resulting GROUP BY.

7. Include the resulting HAVING.

Do NOT provide only the newly added expression in
select_expressions if existing expressions must remain.


============================================================
IMPORTANT FEATURE RULE
============================================================

The "feature" object identifies the primary requested feature
being introduced by the operation.

The "changes.select_expressions" may contain additional columns
or expressions required to support that feature.

For example:

    feature:
        alias: fan_hua
        expression: SUM(67attr - 69attr) AS fan_hua

while:

    changes.select_expressions:
        [
            customer_id,
            total_amount,
            SUM(67attr - 69attr) AS fan_hua
        ]

is valid.

Additional SELECT expressions in "changes" are dependencies or
existing expressions required by the resulting CTE.

Do NOT assume every expression in select_expressions must appear
in the feature object.


============================================================
IMPORTANT USER SQL DEPENDENCY RULE
============================================================

When USER SQL contains:

    CTEa -> CTEb -> CTEc

the planner must preserve the dependency relationship.

However, this does NOT mean the planner must create:

    cte_user_1 -> cte_user_2 -> cte_user_3

If the transformations can be integrated into:

    cte_level_1 -> cte_level_2 -> cte_level_3

then modify the existing CTEs instead.

If a USER SQL CTE depends on a column produced by an existing
CTE, preserve that existing dependency.

Never create a disconnected CTE chain that references columns
which are unavailable from its FROM source.


============================================================
IMPORTANT
============================================================

Do NOT return the complete modified SQL.

Do NOT rewrite the entire existing SQL.

Do NOT generate a complete YAML file.

Return only an EDIT PLAN.


============================================================
OUTPUT FORMAT
============================================================

Return valid JSON only.

Use this structure:

{
    "status": "ready",
    "operations": [
        {
            "operation": "ADD_TO_EXISTING_CTE",
            "target": {
                "cte_name": "example_cte"
            },
            "new_cte_name": null,
            "feature": {
                "alias": "new_feature",
                "expression": "SQL expression"
            },
            "changes": {
                "select_expressions": [],
                "from": null,
                "joins": [],
                "where": null,
                "group_by": [],
                "having": null
            }
        }
    ],
    "reason": "Short explanation.",
    "confidence": 0.90
}


The "operations" array may contain multiple operations.

For example, a request may require:

1. ADD_TO_EXISTING_CTE
2. ADD_TO_EXISTING_CTE
3. MODIFY_FINAL_SELECT

or:

1. ADD_TO_EXISTING_CTE
2. CREATE_NEW_CTE
3. MODIFY_FINAL_SELECT

Do not force the request into a single operation.


============================================================
CHANGES REQUIREMENT
============================================================

For EVERY operation, "changes" must contain the complete SQL
structure affected by that operation.

The "changes" object MUST always contain these fields:

{
    "select_expressions": [],
    "from": null,
    "joins": [],
    "where": null,
    "group_by": [],
    "having": null
}

Do not omit any of these fields.


============================================================
CREATE_NEW_CTE OUTPUT RULE
============================================================

For CREATE_NEW_CTE:

- target.cte_name must be null
- new_cte_name must contain a reasonable unique name
- changes.from must NOT be null when the CTE requires a FROM source
- changes.from must identify a real USER SQL or EXISTING CTE source


============================================================
MODIFY_FINAL_SELECT OUTPUT RULE
============================================================

For MODIFY_FINAL_SELECT:

- target.cte_name must be null
- new_cte_name must be null
- changes must describe the resulting final SELECT structure


============================================================
REQUIRES CONFIRMATION OUTPUT
============================================================

If the correct modification cannot be determined safely, return:

{
    "status": "requires_confirmation",
    "operations": [],
    "reason": "Explain why the decision is ambiguous.",
    "confidence": 0.50,
    "options": []
}


============================================================
CRITICAL JSON REQUIREMENT
============================================================

The TOP-LEVEL JSON response MUST be an OBJECT.

It MUST NOT be a JSON ARRAY.

CORRECT:

{
    "status": "ready",
    "operations": [
        {
            "operation": "ADD_TO_EXISTING_CTE"
        }
    ],
    "reason": "...",
    "confidence": 0.90
}

INCORRECT:

[
    {
        "operation": "ADD_TO_EXISTING_CTE"
    }
]

Even if there is only ONE operation, you MUST return the object
containing the "operations" array.


============================================================
FINAL REQUIREMENT
============================================================

Return JSON only.

No markdown.

No explanation outside the JSON.
"""

    # Insert dynamic values AFTER creating the normal string.
    prompt = prompt.replace(
        "__USER_SQL__",
        user_sql
    )

    prompt = prompt.replace(
        "__USER_STRUCTURE__",
        user_structure_json
    )

    prompt = prompt.replace(
        "__EXISTING_FILE__",
        existing_file
    )

    prompt = prompt.replace(
        "__EXISTING_STRUCTURE__",
        existing_structure_json
    )

    return prompt
# ASK LLM
def ask_llm(prompt):

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )

    text = response.text.strip()

    # Remove accidental markdown fences
    if text.startswith("```json"):
        text = text[7:]

    if text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            "LLM did not return valid JSON.\n\n"
            f"LLM response:\n{text}"
        ) from e

    # VALIDATE TOP-LEVEL RESPONSE
    if isinstance(result, list):
        result = {
            "status": "ready",
            "operations": result,
            "reason": "LLM returned operations as a top-level list.",
            "confidence": None
        }

    elif not isinstance(result, dict):

        raise ValueError(
            "LLM response must be a JSON object."
        )

    return result

# PLAN EDIT FOR ONE YAML
def plan_yaml_edit(yaml_file, user_sql):

    # 1. Parse user SQL
    user_structure = parse_user_sql(user_sql)

    # 2. Load existing SQL structure
    sql_index = load_json_file( SQL_STRUCTURE_INDEX_FILE)

    if yaml_file not in sql_index:
        raise ValueError(
            f"{yaml_file} does not exist in SQL structure index."
        )

    existing_structure = sql_index[yaml_file]

    # 3. Build prompt
    prompt = build_edit_prompt(
        user_sql=user_sql,
        user_structure=user_structure,
        existing_file=yaml_file,
        existing_structure=existing_structure
    )

    # 4. Ask LLM
    result = ask_llm(prompt)
    return result
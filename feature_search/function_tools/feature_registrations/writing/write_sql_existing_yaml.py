import json
from pathlib import Path

import sqlglot
from sqlglot import exp
import yaml


BASE_DIR = Path(__file__).resolve().parents[3]

YAML_FOLDER = BASE_DIR / "yaml_list"


# LOAD YAML
def load_yaml_file(yaml_file):
    yaml_path = YAML_FOLDER / yaml_file
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"YAML file not found: {yaml_path}"
        )

    with open(yaml_path,"r",encoding="utf-8") as file:
        yaml_data = yaml.safe_load(file)
    return yaml_data


# SAVE YAML
def save_yaml_file(yaml_file, yaml_data):

    yaml_path = YAML_FOLDER / yaml_file

    sql = yaml_data.get("sql", "")

    # Convert escaped newline characters into real newlines
    sql = sql.replace("\\n", "\n")

    # Normalize line endings
    sql = sql.replace("\r\n", "\n").replace("\r", "\n")

    # Remove SQL before dumping the rest of the YAML
    other_data = {
        key: value
        for key, value in yaml_data.items()
        if key != "sql"
    }

    with open(yaml_path,"w", encoding="utf-8") as file:
        # Write normal YAML fields
        yaml.safe_dump(
            other_data,
            file,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False
        )

        # Usde same format as the original YAML
        file.write("sql: |-\n")

        for line in sql.split("\n"):
            file.write(f"  {line}\n")

# FIND CTE
def find_cte(sql_expression,cte_name):

    with_clause = sql_expression.args.get("with_")
    if not with_clause:
        return None

    for cte in with_clause.expressions:
        if cte.alias.lower() == cte_name.lower():
            return cte

    return None

def resolve_select_expression(expression_text, existing_expressions):
    expression_text = expression_text.strip()

    # 1. Resolve existing aliases
    for existing_expression in existing_expressions:
        alias = existing_expression.alias

        if alias and alias.lower() == expression_text.lower():
            return existing_expression.copy()

    # 2. Otherwise parse as a new SELECT expression
    parsed = sqlglot.parse_one(
        f"SELECT {expression_text}",
        dialect="maxcompute"
    )

    return parsed.expressions[0]

#Create CTE 
def create_new_cte(sql_expression, cte_name, changes):
    if not cte_name:
        raise ValueError(
            "CREATE_NEW_CTE requires new_cte_name."
        )

    if not isinstance(changes, dict):
        raise ValueError(
            "CREATE_NEW_CTE 'changes' must be an object."
        )

    # SELECT
    select_expressions = changes.get("select_expressions", [])

    if not isinstance(select_expressions, list):
        raise ValueError(
            "'select_expressions' must be a list."
        )

    if not select_expressions:
        raise ValueError(
            "New CTE must contain at least one "
            "SELECT expression."
        )

    # Parse SELECT expressions
    parsed_selects = []

    for expression_sql in select_expressions:
        if not isinstance(expression_sql, str):
            raise ValueError(
                "Every select expression must be a string."
            )
        expression = sqlglot.parse_one(expression_sql, dialect="maxcompute")
        parsed_selects.append(expression)

    # CREATE SELECT
    new_select = exp.Select(expressions=parsed_selects)

    # FROM
    from_clause = changes.get("from")

    if from_clause:
        if isinstance(from_clause, str):
            parsed_from = sqlglot.parse_one(
                f"SELECT * FROM {from_clause}",
                dialect="maxcompute"
            )

            from_expression = (parsed_from.args["from_"])
            new_select.set("from_", from_expression)

        elif isinstance(from_clause, dict):
            table = from_clause.get("table")
            alias = from_clause.get("alias")

            if not table:
                raise ValueError(
                    "FROM object does not contain 'table'."
                )

            from_sql = table

            if alias:
                from_sql += f" AS {alias}"

            parsed_from = sqlglot.parse_one(
                f"SELECT * FROM {from_sql}",
                dialect="maxcompute"
            )

            new_select.set(
                "from_",
                parsed_from.args["from_"]
            )

    # JOINS
    joins = changes.get("joins", [])

    for join in joins:
        source = join.get("source")

        if not source:
            raise ValueError("JOIN is missing 'source'.")

        join_type = join.get("type", "INNER JOIN")

        on_condition = join.get("on")

        join_sql = f"{join_type} {source}"

        if on_condition:
            join_sql += f" ON {on_condition}"

        # Parse a temporary SELECT containing this JOIN
        temp_sql = (
            "SELECT * FROM dummy "
            + join_sql
        )

        parsed_join = sqlglot.parse_one(
            temp_sql,
            dialect="maxcompute"
        )

        for join_expression in parsed_join.args.get("joins",[]):
            new_select.args.setdefault("joins",[]).append(join_expression)

    # WHERE
    where = changes.get("where")

    if where:
        where_expression = sqlglot.parse_one(
            f"SELECT * FROM dummy WHERE {where}",
            dialect="maxcompute"
        )

        new_select.set("where", where_expression.args["where"])

    # GROUP BY
    group_by = changes.get("group_by", [])

    if group_by:
        parsed_group = []

        for expression_sql in group_by:
            parsed_expression = sqlglot.parse_one(
                f"SELECT {expression_sql}",
                dialect="maxcompute"
            )
            parsed_group.append(parsed_expression.expressions[0])
        new_select.set("group",exp.Group( expressions=parsed_group))

    # HAVING
    having = changes.get("having")
    if having:

        parsed_having = sqlglot.parse_one(
            f"SELECT * FROM dummy HAVING {having}",
            dialect="maxcompute"
        )

        new_select.set(
            "having",
            parsed_having.args["having"]
        )

    # CREATE CTE
    new_cte = exp.CTE(
        this=new_select,
        alias=exp.TableAlias(
            this=exp.Identifier(
                this=cte_name
            )
        )
    )

    # Add to WITH
    with_clause = sql_expression.args.get("with_")

    if with_clause is None:
        with_clause = exp.With(expressions=[])

        sql_expression.set(
            "with_",
            with_clause
        )
    with_clause.append("expressions", new_cte)
    return sql_expression

#Add feature to final_select
def add_feature_to_final_select(
    sql_expression,
    feature_expression,
    feature_alias
):

    if not isinstance(sql_expression, exp.Select):
        raise ValueError(
            "The SQL does not contain a "
            "top-level final SELECT."
        )

    expression = sqlglot.parse_one(
        feature_expression,
        dialect="maxcompute"
    )

  
    if (feature_alias and feature_expression.strip().lower() != feature_alias.strip().lower()):
        expression = exp.alias_(
            expression,
            feature_alias
        )

    sql_expression.set(
        "expressions",
        sql_expression.expressions + [expression]
    )

    return sql_expression

# ADD FEATURE TO CTE
def add_feature_to_cte(sql_expression, cte_name, changes):
    cte = find_cte(sql_expression, cte_name)

    if cte is None:
        raise ValueError(
            f"CTE '{cte_name}' was not found."
        )

    cte_query = cte.this

    if isinstance(cte_query, exp.Subquery):
        cte_query = cte_query.this

    select_expressions = changes.get("select_expressions", [])

    if not select_expressions:
        raise ValueError(
            f"ADD_TO_EXISTING_CTE for '{cte_name}' "
            "requires 'changes.select_expressions'."
        )

    parsed_expressions = []

    for expression_sql in select_expressions:
        if not isinstance(expression_sql, str):
            raise ValueError(
                "Every select expression must be a string."
            )

        parsed_expression = sqlglot.parse_one(
            expression_sql,
            dialect="maxcompute"
        )

        parsed_expressions.append(parsed_expression)

    existing_expressions = cte_query.expressions

    new_expressions = []

    for expression_text in changes.get("select_expressions", []):

        expression = resolve_select_expression(
            expression_text,
            existing_expressions
        )

        new_expressions.append(expression)

    # Replace the entire SELECT projection
    cte_query.set(
        "expressions",
        new_expressions
    )

    # --------------------------------------------------
    # FROM
    # --------------------------------------------------

    from_info = changes.get("from")

    if from_info:
        from_expression = build_from_expression(from_info)

        if from_expression:
            from_sql = from_expression.sql(
                dialect="maxcompute"
            )

            parsed_from = sqlglot.parse_one(
                f"SELECT * FROM {from_sql}",
                dialect="maxcompute"
            )

            cte_query.set(
                "from_",
                parsed_from.args["from_"]
            )

    # JOINS
    joins = []

    for join_info in changes.get("joins", []):
        source = join_info.get("source")

        if not source:
            continue

        source_expression = build_from_expression(source)

        join_expression = exp.Join(
            this=source_expression
        )

        on_expression = join_info.get("on")

        if on_expression:
            join_expression.set(
                "on",
                sqlglot.parse_one(
                    on_expression,
                    dialect="maxcompute"
                )
            )

        join_type = join_info.get(
            "type",
            "INNER JOIN"
        ).upper()

        if "LEFT" in join_type:
            join_expression.set("side", "LEFT")
        elif "RIGHT" in join_type:
            join_expression.set("side", "RIGHT")
        elif "FULL" in join_type:
            join_expression.set("side", "FULL")

        joins.append(join_expression)

    cte_query.set("joins", joins)

    # WHERE
    where = changes.get("where")

    if where:
        cte_query.set(
            "where",
            exp.Where(
                this=sqlglot.parse_one(
                    where,
                    dialect="maxcompute"
                )
            )
        )
    else:
        cte_query.set("where", None)

    # --------------------------------------------------
    # GROUP BY
    # --------------------------------------------------

    group_by = changes.get("group_by", [])

    if group_by:
        cte_query.set(
            "group",
            exp.Group(
                expressions=[
                    sqlglot.parse_one(
                        expression,
                        dialect="maxcompute"
                    )
                    for expression in group_by
                ]
            )
        )
    else:
        cte_query.set("group", None)

    # --------------------------------------------------
    # HAVING
    # --------------------------------------------------

    having = changes.get("having")

    if having:
        cte_query.set(
            "having",
            exp.Having(
                this=sqlglot.parse_one(
                    having,
                    dialect="maxcompute"
                )
            )
        )
    else:
        cte_query.set("having", None)

    return sql_expression

def structure_to_sql(structure):

    if not structure:
        raise ValueError(
            "SQL structure is empty."
        )

    structure_type = structure.get("type")

    # SELECT
    if structure_type == "select":
        select_expressions = structure.get("select",[])

        if not select_expressions:
            raise ValueError(
                "SELECT structure does not contain "
                "any select expressions."
            )

        sql_parts = []

        # SELECT
        sql_parts.append("SELECT " + ", ".join(select_expressions))

        # DISTINCT
        if structure.get("distinct"):
            sql_parts[0] = (
                "SELECT DISTINCT " + ", ".join(select_expressions))

        # FROM
        from_info = structure.get("from")

        if from_info:
            from_expression = build_from_expression(from_info)

            sql_parts.append("FROM " + from_expression.sql(dialect="maxcompute"))

        # JOIN
        for join in structure.get("joins", []):

            join_type = join.get("type", "INNER JOIN")
            source = join.get("source")

            if not source:
                continue

            source_expression = build_from_expression(source)

            join_sql = (
                f"{join_type} "
                f"{source_expression.sql(dialect='maxcompute')}"
            )

            on = join.get("on")

            if on:
                join_sql += f" ON {on}"
            sql_parts.append(join_sql)

        # WHERE
        where = structure.get("where")
        if where:
            sql_parts.append(f"WHERE {where}")

        # GROUP BY
        group_by = structure.get("group_by", [])
        if group_by:
            sql_parts.append("GROUP BY " + ", ".join(group_by))

        # HAVING
        having = structure.get("having")
        if having:
            sql_parts.append(f"HAVING {having}")

        # ORDER BY
        order_by = structure.get("order_by",[])
        if order_by:
            sql_parts.append("ORDER BY " + ", ".join(order_by))

        return "\n".join(sql_parts)

    # UNION
    elif structure_type == "union":
        branches = structure.get(
            "branches",
            []
        )

        if not branches:
            raise ValueError(
                "UNION structure contains no branches."
            )

        branch_sql = [
            structure_to_sql(branch)
            for branch in branches
        ]

        return "\nUNION ALL\n".join(
            branch_sql
        )

    else:
        raise ValueError(
            f"Unsupported SQL structure type: "
            f"{structure_type}"
        )

def build_from_expression(from_info):

    if not from_info:
        return None

    from_type = from_info.get("type")
    if from_type in ("table", "cte"):
        table_name = from_info.get("table")
        if not table_name:
            raise ValueError(
                "FROM object does not contain 'table'."
            )

        table = exp.Table(
            this=exp.Identifier(
                this=table_name
            )
        )

        alias = from_info.get("alias")

        if alias:
            table.set(
                "alias",
                exp.TableAlias(
                    this=exp.Identifier(
                        this=alias
                    )
                )
            )

        return table

    elif from_type == "subquery":

        query = from_info.get("query")

        if not query:
            raise ValueError(
                "SUBQUERY FROM object does not contain 'query'."
            )

        subquery_sql = structure_to_sql(query)

        parsed_query = sqlglot.parse_one(
            subquery_sql,
            dialect="maxcompute"
        )

        subquery = exp.Subquery(
            this=parsed_query
        )

        alias = from_info.get("alias")

        if alias:
            subquery.set(
                "alias",
                exp.TableAlias(
                    this=exp.Identifier(
                        this=alias
                    )
                )
            )

        return subquery

    else:
        raise ValueError(
            f"Unsupported FROM type: {from_type}"
        )

# APPLY EDIT PLAN
def apply_edit_plan(yaml_file, edit_plan):

    if edit_plan.get("status") != "ready":
        return {
            "status": "requires_confirmation",
            "plan": edit_plan
        }
    # 1. Check plan status
    if edit_plan.get("status") != "ready":

        return {
            "status": "requires_confirmation",
            "plan": edit_plan
        }

    
    # 2. Load YAML
    yaml_data = load_yaml_file(yaml_file)

    existing_sql = yaml_data.get("sql")

    if not existing_sql:
        raise ValueError(f"No SQL found in {yaml_file}")

    # 3. Parse existing SQL
    sql_expression = sqlglot.parse_one(
        existing_sql,
        dialect="maxcompute"
    )

    # 4. Get operations
    operations = edit_plan.get("operations", [])

    if not operations:
        raise ValueError(
            "Edit plan does not contain any operations."
        )


    # 5. Apply operations in order
    applied_operations = []

    for operation in operations:

        operation_type = operation.get("operation")

        if not operation_type:
            raise ValueError(
                "An edit operation is missing "
                "the 'operation' field."
            )

            # ADD TO EXISTING CTE
        if operation_type == "ADD_TO_EXISTING_CTE":

            target = operation.get("target", {})
            cte_name = target.get("cte_name")

            changes = operation.get("changes", {})

            if not cte_name:
                raise ValueError(
                    "ADD_TO_EXISTING_CTE operation "
                    "does not contain a target CTE."
                )

            if not isinstance(changes, dict):
                raise ValueError(
                    "ADD_TO_EXISTING_CTE 'changes' "
                    "must be an object."
                )

            select_expressions = changes.get(
                "select_expressions",
                []
            )

            if not select_expressions:
                raise ValueError(
                    f"ADD_TO_EXISTING_CTE for '{cte_name}' "
                    "does not contain select_expressions."
                )

            sql_expression = add_feature_to_cte(
                sql_expression=sql_expression,
                cte_name=cte_name,
                changes=changes
            )

            feature = operation.get("feature", {})

            applied_operations.append({
                "operation": operation_type,
                "cte_name": cte_name,
                "feature": feature.get("alias")
            })

        # OTHER OPERATIONS
        # elif operation_type == "MODIFY_EXISTING_CTE":

        #     raise NotImplementedError(
        #         "MODIFY_EXISTING_CTE is not implemented yet."
        #     )
        elif operation_type == "CREATE_NEW_CTE":
                sql_expression = create_new_cte(
                    sql_expression=sql_expression,
                    cte_name=cte_name,
                    changes=changes
                )
            
        elif operation_type == "MODIFY_FINAL_SELECT":
            feature = operation.get("feature", {})
            feature_alias = feature.get("alias")
            feature_expression = feature.get("expression")

            if not feature_expression:
                raise ValueError(
                    "MODIFY_FINAL_SELECT operation "
                    "does not contain a feature expression."
                )

            sql_expression = add_feature_to_final_select(
                sql_expression=sql_expression,
                feature_expression=feature_expression,
                feature_alias=feature_alias
                )

            applied_operations.append({
                "operation": operation_type,
                "feature": feature_alias
            })


        else:

            raise ValueError(
                f"Unknown operation: {operation_type}"
            )

    # 6. Convert SQL AST back to SQL
    new_sql = sql_expression.sql(
        dialect="maxcompute",
        pretty=True
    )
    
    # 7. Update YAML
    yaml_data["sql"] = new_sql

    # 8. Save YAML
    save_yaml_file(
        yaml_file,
        yaml_data
    )

    return {
        "status": "success",
        "yaml_file": yaml_file,
        "operation": operation_type,
        "sql": new_sql
    }
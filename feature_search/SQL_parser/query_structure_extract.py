from sqlglot import exp


def get_expr_name(expr):
    """Safely extracts the true output name of an expression regardless of sqlglot version."""
    if isinstance(expr, exp.Alias):
        return expr.alias
    if isinstance(expr, exp.Column):
        return expr.name
    return getattr(expr, "output_name", getattr(expr, "alias_or_name", ""))



def get_select_aliases(select_node):
    if not isinstance(select_node, exp.Select):
        return []

    aliases = []

    for expression in select_node.expressions:

        if is_star_expression(expression):
            aliases.append("*")
            continue

        name = get_expr_name(expression)

        if name:
            aliases.append(name)

    return aliases

def is_star_expression(expr):
    #SELECT *
    if isinstance(expr, exp.Star):
        return True

    #SELECT a.*
    if isinstance(expr, exp.Column) and expr.is_star:
        return True

    return False


def filter_expressions_for_fields(select_node, required_fields):
    """Filters SELECT expressions to ensure qualified fields are retained."""
    if not isinstance(select_node, exp.Select):
        return []

    if not required_fields:
        return select_node.expressions

    fields_lower = {f.lower() for f in required_fields}
    selected = []

    for expression in select_node.expressions:
        # Keep both * and a.*
        if is_star_expression(expression):
            selected.append(expression)
            continue

        name = get_expr_name(expression)

        if name and name.lower() in fields_lower:
            selected.append(expression)

    return selected


def extract_structure(select, cte_map, required_fields=None):
    if isinstance(select, exp.Union):
        branches = []

        def collect_union_selects(union_node):
            if isinstance(union_node.left, exp.Union):
                collect_union_selects(union_node.left)
            elif isinstance(union_node.left, exp.Select):
                branches.append(union_node.left)

            if isinstance(union_node.right, exp.Union):
                collect_union_selects(union_node.right)
            elif isinstance(union_node.right, exp.Select):
                branches.append(union_node.right)

        collect_union_selects(select)

        extracted_branches = [
            extract_structure(branch,cte_map,required_fields=required_fields) for branch in branches
        ]
        return {
            "type": "union",
            "branches": extracted_branches
        }

    if not isinstance(select, exp.Select):
        return {"type": "unknown"}

    if required_fields is not None:
        if isinstance(required_fields, (list, set)):
            selected_expressions = filter_expressions_for_fields(select, required_fields)
        else:
            selected_expressions = required_fields
    else:
        selected_expressions = select.expressions

    results = {
        "type": "select",
        "select_aliases": get_select_aliases(select),
        "distinct": select.args.get("distinct") is not None,
        "from": None,
        "joins": [],
        "where": None,
        "group_by": [],
        "having": None,
        "order_by": []
    }

    from_clause = select.args.get("from_")

    if from_clause:
        source = from_clause.this

        if isinstance(source, exp.Table):
            full_table_name = (
                source.this.sql()
                if hasattr(source, "this")
                else source.name
            )

            if source.db:
                full_table_name = f"{source.db}.{full_table_name}"

            results["from"] = {
                "type": "cte" if source.name in cte_map else "table",
                "table": full_table_name,
                "alias": source.alias
            }

        elif isinstance(source, exp.Subquery):
            # the subquery instead of converting it to a string.
            results["from"] = {
                "type": "subquery",
                "alias": source.alias,
                "query": extract_structure(
                    source.this,
                    cte_map,
                    required_fields=required_fields
                )
            }

    for join in select.args.get("joins", []):
        join_side = join.args.get("side")
        join_type = f"{join_side} JOIN" if join_side else "INNER JOIN"

        source = join.this

        join_info = {
            "type": join_type,
            "source": None,
            "on": (
                join.args["on"].sql()
                if join.args.get("on")
                else None
            )
        }

        if isinstance(source, exp.Table):
            full_table_name = (
                source.this.sql()
                if hasattr(source, "this")
                else source.name
            )

            if source.db:
                full_table_name = f"{source.db}.{full_table_name}"

            join_info["source"] = {
                "type": "cte" if source.name in cte_map else "table",
                "table": full_table_name,
                "alias": source.alias
            }

        elif isinstance(source, exp.Subquery):
            # Same structure as before, but recursively extract
            # the inner query.
            join_info["source"] = {
                "type": "subquery",
                "alias": source.alias,
                "query": extract_structure(
                    source.this,
                    cte_map,
                    required_fields=required_fields
                )
            }

        results["joins"].append(join_info)

    where = select.args.get("where")

    if where:
        results["where"] = where.this.sql()

    group_by = select.args.get("group")

    if group_by:
        results["group_by"] = [
            expr.sql()
            for expr in group_by.expressions
        ]

    having = select.args.get("having")

    if having:
        results["having"] = having.this.sql()

    order_by = select.args.get("order")

    if order_by:
        results["order_by"] = [
            expr.sql()
            for expr in order_by.expressions
        ]

    return results
from sqlglot import parse_one, exp

from query_structure_extract import (
    extract_structure,
    is_star_expression
)

#Convert SQL -> AST Object
def parse_sql(sql, dialect="maxcompute"):
    return parse_one(sql, dialect=dialect)

#Define CTEs
def build_cte_map(tree):
    cte_map = {}

    for cte in tree.find_all(exp.CTE):
        cte_map[cte.alias] = cte.this

    return cte_map

#Get the Final Select
def get_final_select(tree):
    if isinstance(tree, (exp.Select, exp.Union)):
        return tree

    if isinstance(tree, exp.With):
        return tree.this

    return tree

#Check * (SELECT *, SELECT a.*)
def select_has_star(select):
    if not isinstance(select, exp.Select):
        return False

    return any(
        is_star_expression(e)
        for e in select.expressions
    )

#Get expression (Example: a -> MAX(a) AS a )
def get_field_expressions(select, field_name):

    #Normalize field name
    field_name_lower = field_name.lower()

    #Normal select
    if isinstance(select, exp.Select):
        return [expr for expr in select.expressions if expr.output_name.lower() == field_name_lower]
    
    #Expression in Union
    if isinstance(select, exp.Union):
        results = []
        #Get the field on left side of the Union
        results.extend(get_field_expressions(select.left,field_name))

        #Get the field on the right side of the Union
        results.extend(get_field_expressions(select.right,field_name))

        return results
    return []

#Get the source 
def get_source_tables(select, cte_map):
    sources = []

    if not isinstance(select, exp.Select):
        return sources
    
    #Get the FROM 
    from_clause = select.args.get("from_")

    if from_clause:
        source = from_clause.this

        #Source is Table
        if isinstance(source, exp.Table):
            sources.append({
                "name": source.name,
                "alias": source.alias,
                "type": "cte" if source.name in cte_map else "table"
            })
        #Source is Subquery
        elif isinstance(source, exp.Subquery):
            sources.append({
                "name": source.alias,
                "alias": source.alias,
                "type": "subquery",
                "expression": source.this
            })

    #Source is > 1 (Joined Sources)
    for join in select.args.get("joins", []):
        source = join.this
        #Join Table
        if isinstance(source, exp.Table):
            sources.append({
                "name": source.name,
                "alias": source.alias,
                "type": "cte" if source.name in cte_map else "table"
            })

        #Join Subquery
        elif isinstance(source, exp.Subquery):
            sources.append({
                "name": source.alias,
                "alias": source.alias,
                "type": "subquery",
                "expression": source.this
            })

    return sources

#Find the which sources, columns belong to (Example: a.featureA -> featureA belongs to source a/alias a)
def find_source_for_column(select_node, column_ast, cte_map):
    sources = get_source_tables(select_node, cte_map)

    if not sources:
        return None
    
    #Only one source
    if len(sources) == 1:
        return sources[0]
    
    #Get Column's table name
    table_ref = (column_ast.table if isinstance(column_ast, exp.Column) else None)
    col_name = (column_ast.name if isinstance(column_ast, exp.Column) else str(column_ast))


    # Get source for columns:
    if table_ref:
        table_ref_lower = table_ref.lower()

        for source in sources:
            #FROM customer c
            if (source.get("alias") and source["alias"].lower() == table_ref_lower):
                return source
            #FROM customer
            if (source.get("name") and source["name"].lower() == table_ref_lower):
                return source
            #FROM abc.customer
            if (source.get("name") and source["name"].lower().endswith("." + table_ref_lower)):
                return source

    # Try to determine which CTE contains the column.
    for source in sources:
        if source["type"] == "cte":
            cte_name = source["name"]
            cte_select = cte_map.get(cte_name)
            if cte_select:
                exprs = get_field_expressions(cte_select,col_name)
                if exprs or select_has_star(cte_select):
                    return source
    # Fallback
    return sources[0]


CURRENT_CTE_MAP = {}


def trace_field(tree, field_name):

    global CURRENT_CTE_MAP
    cte_map = build_cte_map(tree)
    CURRENT_CTE_MAP = cte_map
    lineage = []
    visited = set()
    required_fields = {}

    structure = {
        "final": None,
        "ctes": {}
    }

    # Save all necessary fields inside 1 CTE
    def require_field(cte_name, field):

        if cte_name not in required_fields:
            required_fields[cte_name] = set()

        required_fields[cte_name].add(field)

    # LINEAGE (save connection for example: order_id -> customer.order_id)
    def add_lineage(item):
        if item not in lineage:
            lineage.append(item)

    # CLAUSE DEPENDENCIES (Check fields that are not in the SELECT)
    def capture_clause_dependencies(select_node,current_cte):
        if not isinstance(select_node, exp.Select):
            return

        clauses_to_check = []

        #Get WHERE dependencies
        if select_node.args.get("where"):
            clauses_to_check.append(select_node.args["where"])

        #Get GROUP BY dependencies
        if select_node.args.get("group"):
            clauses_to_check.append(select_node.args["group"])

        #Get HAVING dependencies
        if select_node.args.get("having"):
            clauses_to_check.append(select_node.args["having"])

        #Get JOIN dependencies
        for join in select_node.args.get("joins", []):

            if join.args.get("on"):
                clauses_to_check.append(join.args["on"])

        for clause in clauses_to_check:

            for col in clause.find_all(exp.Column):
                col_name = col.name

                #Get sources for all dependency columns
                target_source = find_source_for_column(select_node,col,cte_map)

                if target_source:
                    #Source is CTE
                    if target_source["type"] == "cte":
                        #Add parameters to required_field
                        require_field(target_source["name"],col_name)

                        #Recursive trace back
                        trace_cte(target_source["name"],col_name)

                    #Source is table
                    elif target_source["type"] == "table":
                        #Immediately append to lineage
                        add_lineage({
                            "field": col_name,
                            "source": (
                                f"{target_source['name']}"
                                f".{col_name}"
                            ),
                            "cte": current_cte
                        })

                    #Source is subquery
                    elif target_source["type"] == "subquery":
                        trace_subquery(target_source["expression"], current_cte, col_name)

    # TRACE A COLUMN -> Recursively track a column
    def trace_column(select, current_cte, column_ast):
        col_name = (column_ast.name if isinstance(column_ast, exp.Column) else str(column_ast))
        source = find_source_for_column(select,column_ast, cte_map)

        if not source:
            return

        # Source is CTE
        if source["type"] == "cte":
            upstream_cte = source["name"]
            require_field( upstream_cte, col_name)

            add_lineage({
                "field": col_name,
                "source": f"{upstream_cte}.{col_name}",
                "cte": current_cte
            })

            trace_cte(upstream_cte, col_name)

        # Source is Table
        elif source["type"] == "table":
            add_lineage({
                "field": col_name,
                "source": f"{source['name']}.{col_name}",
                "cte": current_cte
            })
        
        #Source is Subquery
        elif source["type"] == "subquery":
            trace_subquery(source["expression"],current_cte,col_name)

    # TRACE UNION (Check left side of union and right side of union)
    def trace_union(union, current_cte, requested_field):
        #Get the left side of the Union branch
        trace_union_branch(union.left, current_cte, requested_field)

        #Get the right side of the Union branch
        trace_union_branch(union.right,current_cte,requested_field)

    def trace_union_branch(branch,current_cte,requested_field):
        #Union inside Union
        if isinstance(branch, exp.Union):
            trace_union(branch,current_cte,requested_field)
            return

        if not isinstance(branch, exp.Select):
            return

        #Get Dependencies
        capture_clause_dependencies(branch,current_cte )

        #Get expressions
        expressions = get_field_expressions(branch,requested_field)

        if not expressions:
            #Check * Selection
            if select_has_star(branch):
                #Get the Sources 
                sources = get_source_tables(branch,cte_map)

                for source in sources:
                    trace_source(source,current_cte,requested_field)
            return

        # Normal expression
        for expression in expressions:
            #Select Columns
            expression_body = (expression.this if isinstance(expression, exp.Alias) else expression)

            columns = list(expression_body.find_all(exp.Column) )

            for column in columns:
                trace_column(branch,current_cte,column)

    # Trace Sources (For SELECT *)
    def trace_source(source,current_cte,column_name):

        # Source is CTE
        if source["type"] == "cte":

            require_field(source["name"],column_name)

            add_lineage({
                "field": column_name,
                "source": (
                    f"{source['name']}"
                    f".{column_name}"
                ),
                "cte": current_cte
            })

            trace_cte(
                source["name"],
                column_name
            )

        # Source is Table
        elif source["type"] == "table":

            add_lineage({
                "field": column_name,
                "source": (
                    f"{source['name']}"
                    f".{column_name}"
                ),
                "cte": current_cte
            })

       
        #Source is Subquery
        elif source["type"] == "subquery":
            trace_subquery(source["expression"],current_cte,column_name)


    #Trace Subquery
    def trace_subquery(subquery_select, current_cte, requested_field):
      
        #Union inside Subquery
        if isinstance(subquery_select, exp.Union):  
            trace_union(subquery_select,current_cte,requested_field)
            return

        if not isinstance(subquery_select,exp.Select):
            return
    
        #Get dependencies
        capture_clause_dependencies(subquery_select,current_cte)

        # Find expression producing requested field
        expressions = get_field_expressions(subquery_select, requested_field)
       
        #If SELECT *
        if not expressions:
            if select_has_star(subquery_select):
                sources = get_source_tables(subquery_select,cte_map)
                for source in sources:
                    trace_source(source,current_cte,requested_field)
            return

        # Normal SELECT expression
        for expression in expressions:
            expression_body = (expression.this if isinstance(expression, exp.Alias) else expression)
            columns = list( expression_body.find_all(exp.Column))
            for column in columns:
                trace_column(subquery_select,current_cte,column)

    # Trace CTE
    def trace_cte(cte_name, requested_field):
        key = (cte_name.lower(),requested_field.lower())

        if key in visited:
            return

        visited.add(key)

        actual_name = None
        select = None

        for name, value in cte_map.items():
            if name.lower() == cte_name.lower():
                actual_name = name
                select = value
                break

        if select is None:
            return

        # Trace Union inside CTE
        if isinstance(select, exp.Union):
            require_field(actual_name, requested_field)
            trace_union(select, actual_name,requested_field)
            return

        if not isinstance(select, exp.Select):
            return

        # Clause dependencies
        capture_clause_dependencies(select,actual_name)

        # Find expression producing requested field
        expressions = get_field_expressions(select,requested_field)

        
        #If SELECT *
        if not expressions:

            if select_has_star(select):
                require_field(actual_name, requested_field)
                sources = get_source_tables(select, cte_map)

                for source in sources:
                    trace_source(source, actual_name, requested_field)

                    
        # Normal expression
        for expression in expressions:
            require_field(
                actual_name,
                requested_field
            )
            expression_body = (
                expression.this
                if isinstance(expression, exp.Alias)
                else expression
            )
            columns = list(
                expression_body.find_all(exp.Column)
            )
            seen_columns = set()

            for column in columns:
                column_name = column.name
                if column_name.lower() in seen_columns:
                    continue
                seen_columns.add(column_name.lower())
                trace_column(select,actual_name,column)

    # FINAL SELECT
    final_select = get_final_select(tree)

    # Final UNION
    if isinstance(final_select,exp.Union):

        structure["final"] = {
            "type": "union"
        }
        trace_union(final_select, "FINAL", field_name)

    
    # Normal final SELECT
    elif isinstance(final_select,exp.Select):
        #Process all dependencies
        capture_clause_dependencies(final_select,"FINAL")

        #Process final Select (Normal)
        structure["final"] = extract_structure(final_select,cte_map,required_fields=[field_name])

        #Get the expression
        expressions = get_field_expressions(final_select,field_name)

        #SELECT *    
        if not expressions:
            if select_has_star(final_select):
                sources = get_source_tables(final_select,cte_map)

                #Process all columns through sources
                for source in sources:
                    trace_source(source, "FINAL", field_name)

        
        # Normal expression
        else:
            for expression in expressions:
                expression_body = (expression.this if isinstance(expression, exp.Alias) else expression)
                columns = list(expression_body.find_all(exp.Column))

                #Process all columns
                for column in columns:
                    trace_column(final_select,"FINAL",column)

    # BUILD STRUCTURE 
    for cte_name, fields in required_fields.items():
        select = None
        for name, value in cte_map.items():
            if name.lower() == cte_name.lower():
                select = value
                break

        if select is None:
            continue

        structure["ctes"][cte_name] = extract_structure(select, cte_map, required_fields=fields)

    # FINAL RESULT
    return {
        "field": field_name,
        "lineage": lineage,
        "required_fields": {
            cte: sorted(fields)
            for cte, fields in required_fields.items()
        },

        "structure": structure
    }
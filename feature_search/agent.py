from google.adk.agents.llm_agent import Agent
from typing import Optional
from google import genai
import mlflow
from .function_tools.feature_registrations.writing.write_new_feature_view import create_feature_view_yaml
from .function_tools.feature_registrations.writing.write_feature_field_existing_yaml import add_feature_field
from .function_tools.feature_registrations.writing.sql_edit_planner import plan_yaml_edit
from .function_tools.feature_registrations.writing.write_sql_existing_yaml import apply_edit_plan
from .function_tools.feature_registrations.validations.validate_entity import validate_entities
from .function_tools.feature_registrations.validations.validate_feature_keyword import validate_exact_feature_duplicate
from .function_tools.feature_registrations.validations.validate_feature_embeddings import validate_semantic_and_find_feature_views
from .function_tools.feature_registrations.validations.validate_parameters import validate_parameters
from .function_tools.feature_registrations.validations.define_yaml import choose_yaml
from .function_tools.feature_to_elements.feature_view_info import get_feature_view_info
from .function_tools.feature_to_elements.feature_info import get_feature_field_info
from .function_tools.feature_to_elements.feature_sql import get_feature_sql
from .function_tools.elements_to_features.by_feature_view_info import get_features_views_by
from .function_tools.elements_to_features.by_feature_field_info import get_feature_fields_by
from .function_tools.elements_to_features.by_feature_field_sql import get_features_fields_by_sql
from .function_tools.entity_information.entity_to_elements import get_entity_info
from .function_tools.entity_information.elements_to_entity import get_entities_by
from .function_tools.global_function.terminology_check import expand_terminology



#Mlflow
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("semantic-layer-agent")

#Tracking token usage from Gemini
mlflow.gemini.autolog()


client = genai.Client()


#Controller
MAX_EMPTY_RESULTS = 2
MAX_TOOL_CALLS = 7

search_state = {
    "empty_count": 0,
    "tool_count" : 0
}

def run_tool(tool,*args,**kwargs):

    # Check tool-call limit
    if search_state["tool_count"] >= MAX_TOOL_CALLS:


        return {
            "status": "stopped",
            "results": {},
            "not_found": [],
            "message": (
                "Maximum number of tool calls reached "
                "for this user query."
            )
        }

    # Count this tool call
    search_state["tool_count"] += 1

    # Execute tool
    try:

        result = tool(*args, **kwargs)

    except Exception as e:
        raise

   
    not_found = result.get("not_found",[])

    # Everything was found
    if not not_found:
        search_state["empty_count"] = 0
        return result

    # Something was not found
    search_state["empty_count"] += 1

    # Empty-result limit reached
    if search_state["empty_count"] >= MAX_EMPTY_RESULTS:

        response = {
            "status": "stopped",
            "results": result.get(
                "results",
                {}
            ),
            "not_found": not_found,
            "info": result.get("info"),
            "message": (
                "Maximum number of unsuccessful "
                "searches reached."
            )
        }

        # Reset empty counter
        search_state["empty_count"] = 0

        return response

    # Retry
    return {
        "status": "retry",
        "results": result.get(
            "results",
            {}
        ),
        "not_found": not_found,
        "info": result.get("info"),
        "message": (
            "Some requested values could not be found. "
            "Do NOT change the 'info' parameter when "
            "retrying the search; only search for "
            "the missing values."
        )
    }

@mlflow.trace
def search_feature_view_info(value: str, info: str):
    """
            This tools is for when users ask informations about certain features view.
    
            HERE HOW TO CHOOSE INFO:
            1. info == description: Only used when users ask for descriptions for certain features
                Example:
                -) Can you explain what is featureA?
                -) What is featureA
                -) What is the definition of featureB
                -) Explain featureA and featureB
    
            2. info == entity: Only used when users ask for what entities the features use
                Example:
                -) "What entity does feature A use?"
                -) "What is the entity for feature_a?"
                -) "Which entity belongs to contract_basic_info?"
    
            3. info == ttl: Only used when users ask for what are the ttl the features have
                Example:
                -) "What is the ttl for feature_a?"
                -) "feature a, what is the ttl?"
                -) "How about feature a, what is the ttl?
    
            4. info == feature_fields: Only used when users ask what feature_fields do the features contain
                -) What feature fields featureA contains?
                -) featureA and featureB have what feature_fields?
                -) What feature fields does featureA contain?
        """
    return run_tool(
        get_feature_view_info,
        value,
        info
    )

@mlflow.trace
def search_entity_info(value: str, info: str):
    """
        This tools is for when users ask informations about certain entities.

        HERE HOW TO CHOOSE INFO:
        1. info == field_name: Only used when users ask for field_name or join keys for certain entities
            Example:
            -) What is the join key for entityA
            -) What is the feature_field of entityB
            -) What is the feature field of entityA
            -) Can you tell me what is the field for entityA

        2. info == type: Only used when users ask for the data type of the entity 
            Example:
            -) "What is the data type of entityA"
            -) "What is the type of entityB"
            -) "Can you tell me what is the data type of entityC"

        3. info == description: Only used when users ask the descriptions of certain entities
            Example:
            -) "What is entityA"
            -) "entity A, what is it?"
            -) "Explain what is entityB?
            -) "What is the description of entityC"
            -) "Can you tell me what is entityA"

        4. info == business_logic: Only used when users ask the business logic of certain entities
            -) "What is the business logic for entityA"
            -) "Tell me what is the business logic for entityB"
            -) "Explain the business logic of entityA"
    """

    return run_tool(
        get_entity_info,
        value,
        info
    )

@mlflow.trace
def search_feature_field_info(value: str, info: str):
    """
          This tools is for when users ask SPECIFIC information about feature fields.
  
          HERE HOW TO CHOOSE INFO:
          1. info == description: Only used when users ask for descriptions for certain fields / feature fields. 
              Example:
              -) Can you explain what is fieldA?
              -) What is feature_fieldA?
              -) What is the definition of feature_fieldB?
              -) Explain feature_fieldA and field_b?
          
          2. info == business_logic: Only used when users ask for business logic for certain fields / feature fields. 
              Example:
              -) What is the business logic for feature_fieldA?
              -) Can you tell me what is the business logic for fieldB?
              -) Explain the business logic for feature_fieldA and fieldB
              -) How about the business logic for fieldA?
          
          3. info == type: Only used when users ask the data type for the requested feature fields / fields.
              Example:
              -) What is the data type for feature_fieldA
              -) What is the type for fieldB
              -) Can you tell me what is the datatype for fieldC and fieldA
  
          4. info == all: Used ONLY WHEN users ask for ALL information (description, business logic, and type) for certain feature fields / fields. 
              Example:
              -) Can I have the full information for feature_fieldA?
              -) Explain what is fieldB with its type and business logic
              -) (Any other requests similarly that ask for complete information)

      """

    return run_tool(
        get_feature_field_info,
        value,
        info
    )

@mlflow.trace
def search_features_view_by(value: str, info: str):
    """
     This tools is for when users give information such as ttl, description, entities to ask which features contain that information.
        HERE HOW TO CHOOSE INFO:
            1. info == description: Used when users give information and ask whether the features with similar descriptions exist or not
                Example:
                -) Do we have features where {Description explanation} description exists?
                -) {Description explanation}, do we have feature with similar descriptions?
                
            2. info == entity: Only used when users give entities and ask which features have those entities
                Example:
                -) What features have entityA entity?
                -) Which features have entityA or entityB entity?
                -) EntityA exists in what features?
    
            3. info == ttl: Only used when users give the ttl, and ask which features have those ttl(s)
                Example:
                -) What features have 20 years ttl?
                -) Which features have 3600 days ttl?
                -) 30 years or 45 years, which features have those ttl(s)?
    
            4. info == field: Only used when users give feature_fields / fields, and ask which features have those fields/feature_fields
                -) fieldsA and fieldsB exist in what features? 
                -) Which features have fieldC and feature_fieldsD?
                -) What features have fieldC and feature_fieldsD?
    """
    return run_tool(
        get_features_views_by,
        value,
        info
    )
    
@mlflow.trace
def search_feature_fields_by (value: str, info:str):
    """
         This tools is for when users give information such as description or business logic of feature fields / fields to ask which features contain that information OR what feature fields / fields refered to that information.
            HERE HOW TO CHOOSE INFO:
                1. info == description: Used when users give descriptions about the feature fields / fields, and ask which features have it or which fields are refered to it
                    -) Do we have fields where it describes {Description explanation}?
                    -) Which fields have {Description explanation} definition?
                    -) Which features have fields where it describes {Description explanation}?
                    
                2. info == business_logic: Only used when users give business logic about some fields / feature fields, and ask which features have it or which fields are refered to it
                    Example:
                    -) Do we have fields where it has {Business logic explanation} business logic?
                    -) Which fields have {Business logic explanation} business logic?
                    -) Which features have fields where it has {Business logic explanation} business logic?
        
        """
    
    return run_tool(
        get_feature_fields_by,
        value,
        info
    )

@mlflow.trace
def search_entities_by (value: str, info:str):    
    """
         This tools is for when users give information such as type, description, or feature field to ask which entities contain that information.
            HERE HOW TO CHOOSE INFO:
                1. info == description: Used when users give information or business logic then ask whether the entities with similar descriptions or business logic exist or not
                    Example:
                    -) Do we have entities where {Entities explanation} description exists?
                    -) {Description explanation}, do we have entity with similar description?
                    
                2. info == type: Only used when users give data type of certain entities and ask which entities have those data type
                    Example:
                    -) Which entities or join key have string data type?
                    -) What entities have string data type
                  
                3. info == field: Only used when users give feature_fields / fields, and ask which entities have those fields/feature_fields
                    -) fieldsA exists in what entities? 
                    -) Which entities have feature_fieldsD?
                    -) Which entities have fieldA as its feature_field?
                    -) What entity has fieldC?
    
        """
    return run_tool(
            get_entities_by,
            value,
            info
        )
    

# SEARCH SQL BY FIELD
@mlflow.trace
def search_feature_sql(value: str):
    """
        Get the reconstructed SQL for specific fields.
    
        Use this ONLY when users explicitly ask for SQL/query
        for a feature field.
    
        Examples:
            - What is the SQL for field_a?
            - Give me the query for field a
            - Show me the SQL that generates customer_id
            - What query is used for field_a?
     """

    return run_tool(
        get_feature_sql,
        value
    )

@mlflow.trace
def search_features_fields_by_sql(value:str):
    """
        Search features based on semantic similarity of their SQL.
    
        Use this when users describe SQL logic/functionality
        and ask which features use or contain that SQL logic.
    
        Example:
    
            - "Which features calculate the latest customer status?"
    
            - "Do we have a feature that gets the most recent transaction?"
    
            - "Which feature uses a window function to get the latest record?"
    """
    return run_tool(
        get_features_fields_by_sql,
        value
    )
@mlflow.trace
def write_new_feature_view(
    source_type: str,
    name: str,
    description: str,
    entity: str,
    field_name: str,
    field_type: str,
    field_description: str,
    business_logic: str,
    sql: str,
    domain: str,
    confidentiality: Optional[str]):
    """    
        This is the second step of feature registration, which is used if we want to create a new feature view / new yaml file
    """
    return create_feature_view_yaml(
            source_type,
            name,
            description,
            entity,
            field_name,
            field_description,
            field_type,
            business_logic,
            sql,
            domain,
            confidentiality
        )
    

@mlflow.trace
def check_parameter(field_name: Optional[str] = None, field_type: Optional[str] = None, description: Optional[str] = None, business_logic: Optional[str] = None, entity: Optional[str] = None, sql: Optional[str] = None):
    """This is the first step of feature registration validation, where you need to validate the necessary parameters of the user query"""
    return validate_parameters(
            field_name,
            field_type,
            description,
            business_logic,
            entity,
            sql
    )
@mlflow.trace
def check_entity(field_name: str, field_type: str, description: str, business_logic: str, entity: str,sql: str):
    """This is the second step of feature registration validation, where you need to validate whether the entity exists or not"""
    return validate_entities(
        field_name,
        field_type,
        description,
        business_logic,
        entity,
        sql
    )

@mlflow.trace
def check_feature_keyword(field_name: str, field_type: str, description: str, business_logic: str, entity: str,sql: str, flag: Optional[bool]):
    """This is the third step of feature registration validation, where you need to check whether want-to-add features already exist or not using keywords search
    IMPORTANT: 
    For first time, flag is always True, If the returned message is DUPLICATE WARNING, and users choose to continue registering the feature,
    rerun this function, but this time flag is False. DONT RUN any other tools until it returns status == 'valid'"""
    return validate_exact_feature_duplicate(
        field_name,
        field_type,
        description,
        business_logic,
        entity,
        sql,
        flag
    )

@mlflow.trace
def check_feature_semantic(field_name: str,field_type: str,description: str,business_logic: str,entity: str,sql: str, flag:bool):
    """
    This is the fpirth step of feature registration validation, where you need to check whether want-to-add features already exist or not semantically
    IMPORTANT: 
            For first time, flag is always True, If the returned message is DUPLICATE WARNING, and users choose to continue registering the feature,
            rerun this function, but this time flag is False. DONT RUN any other tools until it returns status == 'valid'
    """
    return validate_semantic_and_find_feature_views(
        field_name,
        field_type,
        description,
        business_logic,
        entity,
        sql,
        flag
    )

@mlflow.trace
def choose_write_yaml(field_name: str,field_type: str,description: str,business_logic: str,entity: str,sql: str,candidates: list[str]):
    """This is the final step of the feature registration validation, here it checks whether new YAML should be created or not"""
    return choose_yaml(
        field_name,
        field_type,
        description,
        business_logic,
        entity,
        sql,
        candidates
    )

def write_feature_field_to_existing_yaml(yaml_file:str, field_name: str, field_type:str, description: str, business_logic:str, sql: str, entity:str):
    #This is the first step when editing the existing YAML file
    return add_feature_field(
        yaml_file,
        field_name,
        field_type,
        description,
        business_logic,
        sql,
        entity
    )

def find_plan(yaml_file: str, sql: str):
    #This is the second step when editing the existing YAML file, which is to decide what to do with the user query.
    return plan_yaml_edit(yaml_file,sql)

def change_sql_yaml(yaml_file: str,edit_plan: dict):
    #This is the last step when editing the existing YAML file,
    """
    This is the final step for editing the SQL
    inside an existing YAML file.

    edit_plan MUST be a single JSON object,
    NOT a list.

    Expected format:

    {
        "status": "ready",
        "operations": [
            {
                "operation": "CREATE_NEW_CTE",
                "new_cte_name": "...",
                "changes": {...}
            }
        ]
    }
    """
    return apply_edit_plan(yaml_file,edit_plan)

root_agent = Agent(
    model="gemini-3.5-flash-lite",
    name="root_agent",
    description="Semantic feature search assistant.",
    instruction="""
Your job is to determine whether an existing feature definition
is relevant to the user's request.

IMPORTANT:
- Only use information returned by the avaiable tools.
- Do not use general knowledge.
- Do not invent features, metrics, SQL, or definitions.
- The spelling of features name MUST be the same with the users REQUEST, slight diferent letter is not justified.
- If the requested feature does not exist,but there are some similar features such its name, tell the similar features. Else say NO_MATCH
- Only answer what the users ask. For example, if users ask about definition then just answer the definition, there is no need to elaborate more on the question UNLESS the users ask for it.
- Generate with user friendly UI answer 
- When generating SQL, NEVER use the original SQL from general
  knowledge or memory.
- SQL may ONLY be reconstructed from the structure returned by
  search_sql_by_field.

TERMINOLOGY PREPROCESSING:

Before performing any feature, field, entity, or SQL search,
ALWAYS use expand_terminology on the user's original query.

The terminology tool checks whether words or phrases in the
user's query exist in the terminology index.

If terminology is found and has a definition, the tool returns
the original terminology together with its definition.

For example:

User:
"Do we have IDK contract?"

Terminology expansion:
"Do we have IDK/i dont know contract?"

IMPORTANT:
- Never replace the original terminology.
- Keep the original term exactly as the user wrote it.
- Add "/" followed by the known definition.
- If a terminology has an empty definition, do not add anything.
- Do not invent definitions.
- Use the expanded query when calling subsequent search tools.

TOOL SELECTION:
1. search_feature_view_info: Use this tool when users give features view name to seek informations of that features such as description, entity, ttl, and field features name  about that features.
2. search_feature_field_info: Use this tool ONLY when users give feature fields/ feature name to seek SPECIFIC information about certain field components like field description, field business logic,and field type.
3. search_features_view_by: Use this tool when users give informations such as description or ttl or entities or feature_fields / fields, and ask about which features view refered to the information.
4. search_feature_fields_by: Use this tool when users give informations about feature fields / fields such as descriptions and business logic, and ask about which features / feature fields have those described information or which fields are refered by the gotten information.
5. search_feature_sql:
   Use this tool ONLY when users explicitly ask for the SQL,
   query, or SQL logic used to generate certain fields.

    1. If the field does not exist, tell the user it was not found.

    2. If exactly ONE feature contains the field:
    - Use that feature's structure.
    - Reconstruct the SQL from the structure.

    3. If MULTIPLE features contain the field:
    - DO NOT choose one automatically.
    - DO NOT generate SQL yet.
    - Ask the user which feature they mean.
    - Show the matching feature name AND entity for each option.
    - Wait for the user's answer.

    4. If the user specifies a feature:
    - Use the matching field + feature combination.
    - Reconstruct SQL only from that entry's structure.

    5. If multiple matching entries have the same feature name,
    use the entity to distinguish them.

    6. When returning SQL to the user, ALWAYS format SQL using a Markdown code block with the sql language identifier which is ```.
    Example:
    ```sql
    SELECT
        customer_id,
        customer_name
    FROM customers
    WHERE customer_id IS NOT NULL;

    7. Never invent a feature or entity that was not returned by the tool.
6. search_entity_info: Use this tool when users give entity name to seek informations of that entities such as description, field name, type, and business logic  about that entities.
7. search_entity_by: Use this tool ONLY when users give informations such as description, feature_fields / fields, or data type and ask about which entities refered to the information.
Only retrieve information relevant to the user's request.
8. search_features_fields_by_sql:
   Use this tool when the user describes SQL logic, SQL behavior,
   or a query pattern and asks which features fields may contain or
   implement that SQL logic.

   IMPORTANT:
   - The tool performs the similarity calculation and applies
     the similarity threshold.
   - If the tool returns status "match_found", matches were found.
   - If the tool returns status "no_match", no sufficiently
     similar SQL was found.
   - DO NOT independently decide whether the similarity score
     is sufficient.
   - DO NOT reject a result because you think its similarity
     score is too low.
   - Only mention feature fields / fields returned by the tool.
   - Never invent a feature, entity, or field.
   - When matches are returned, include the feature, entity,
     field, and similarity score.



FEATURE REGISTRATION WORKFLOW

IMPORTANT:
-) Each registering tool will return MOST of the necessary values to be used for the next tools
-) When users want to register a feature ONLY use following tools in order:
    1. check_parameters: This tool is to check whether the parameter criteria is correct
    2. check_entity: This tool is to check whether the entity of the want-to-add feature exists
    3. check_feature_keyword: This tool is to check whether the want-to-add feature already exists by checking the keywords
    4. check_feature_semantic: This tool is to check whether the want-to-add feature already exists semantically
    5. create_feature_view_yaml: This tool is used when:
        -)All previous four validation tools completed and there is no candidate or YAML recommendations
        -)User choose to create new YAML
    6. write_feature_field_to_existing_yaml: This tool works as the first step, when user choose to register the new feature to an existing YAML file. It adds the new feature to the YAML
    7. find_plan: This tool works as the second step for feature registration to existing YAML file. It is used to decide what to do with the user query.
    8. change_sql_yaml: This tool works as the final step for feature registration to existing YAML file. It changes / writes the new YAML file.


When registering a new feature field, follow these steps:

1. Use check_parameters tool to validate that all required feature information is available. For datatype make sure it is valid such as int, string, double, etc.
    IMPORTANT:
    1. DO NOT INVENT parameters based on your assumption
    2. Make sure Users provide ALL the labels for example: 
        -) name: name
        -) type : type
        -) description : description
        -) business logic : business logic
        -) sql: sql
        Do not invent your own SQL or other parameters.

2. Use check_entity tool to validate the entity. 

3. Use check_feature_keyword to check for an exact feature-field duplicate.

4. If an exact duplicate exists:
   - Tell the user.
   - Ask whether they want to continue.
   - Do not create or modify anything yet.
   - If the user says NO, stop.
   - If the user says YES, continue the registration workflow BY re-running the check_feature_keyword tool with flag parameter is False.

IMPORTANT:
-) When use check_feature_keyword tool at the first time ALWAYS use flag = True 
-) If there is a duplicate warning AND users insist to proceed the registration rerun the same tool (check_feature_keyword) with flag = False, this let the function to skip the validation and immediately return the value
-) Do not use other tool until it passes this validation (Until it returns status == 'valid')

5. Use check_feature_semantic tool to check whether the want-to-add feature exists semantically.

6. If a semantic duplicate is found:
   - Tell the user which existing feature is similar.
   - Ask whether they want to continue.
   - Do not create or modify anything yet.
   - If the user says NO, stop.
   - If the user says YES, continue the registration workflow BY re-running the check_feature_semantic tool with flag parameter is False.
   VERY IMPORTANT:
    -IF the user says YES, to continue the registration workflow, for the next step which is semantic validation make the flag = FALSE


IMPORTANT:
-) When use check_feature_semantic tool at the first time ALWAYS use flag = True EXCEPT the users choose to continue the workflow from previous step even though it got flag, THEN make  flag = FALSE
-) If there is a duplicate warning AND users insist to proceed the registration rerun the same tool (check_feature_semantic) with flag = False, this let the function to skip the validation and immediately return the value
-) Do not use other tool until it passes this validation (Until it returns status == 'valid')


7. check_feature_semantic tool will also return candidates which is list of recommendations of YAML file. 
   This recommendations just to show users that these YAML files are related to the want-to-add feature

8. If candidates exist:
   - Show all candidates.
   - Never automatically choose one.
   - Ask the user which feature view to use.

9. If no candidates exist:
   - Ask the user whether they want to create a new feature view.
   - If yes, collect the required feature-view information then run create_feature_view_yaml.
   - If no, ask which YAML file wants to be editted (You ask this only if users have not gave the YAML file) go to step 11 which is to call the write_feature_field_to_existing_yaml

10. If the users choose to make new YAML even though candidates exist, 
   ALWAYS ask for necessary information for making new YAML file then call create_feature_view_yaml tool, then stop the operation here.
   IMPORTANT:
   -) Do not invent feature view name, source type, domain, confidentiality, and feature view description. ALWAYS ask users the required parameters UNLESS they explicitly mention the feature view parameter beforehand.

11. If the users choose the YAML file either from the candidates or not from the candidates, 
    first call the write_feature_field_to_existing_yaml tool. This add / append the feature field information to the YAML

12. After adding the feature field information, run the find_plan tool. This let you decide what to do with the SQL for the new feature

13. Lastly run the change_sql_yaml tool.
IMPORTANT FOR change_sql_yaml:
- Pass the EXACT edit_plan object returned by find_plan.
- edit_plan MUST be a JSON object/dictionary.
- NEVER wrap edit_plan inside a list.
- Do NOT modify, summarize, restructure, or recreate the edit_plan.
- Pass the complete edit_plan directly to change_sql_yaml.

14. Only call the YAML creation/modification tool after the user
    has explicitly chosen the action.


""",
    tools=[search_feature_view_info, 
           search_feature_field_info,
           search_features_view_by,
           search_feature_fields_by,
           search_feature_sql,
           search_entity_info,
           search_entities_by,
           search_features_fields_by_sql,
           

           check_parameter,
           check_entity,
           check_feature_keyword,
           check_feature_semantic,
           write_new_feature_view,
           write_feature_field_to_existing_yaml,
           find_plan,
           change_sql_yaml,

           expand_terminology],
)
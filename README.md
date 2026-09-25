<h1>Semantic Layer Project</h1>
<h2>Project Overview</h2>
<br>
The Semantic Layer AI Assistant is an intelligent agent designed to bridge the gap between complex data infrastructure and end-users. It serves as an automated co-pilot that simplifies how data teams and business stakeholders interact with the organization's semantic layer.
<br>
<br>
By unifying vector-based semantic search, deterministic index lookups, and automated code generation, the assistant handles two core workflows: retrieving and explaining existing features and registering new features/entities into the semantic layer.

<h2>Core Features</h2>
<h3>1. Feature Information Retrieval</h3>
<img src="Diagram_sources\Feature Retrieval.png" alt="feature_retrieval_graph">
<li><h3>feature-to-elements</h3>
  <p>
feature-to-elements conversation meanns that users <strong>know</strong> the feature name but seek information regarding that feature elements. For example:</p>
  <ul>
    <li>What is the <strong>business</strong> logic of <strong>featureA</strong>?</li>
    <li>Can you tell me what is the data type of <strong>featureB</strong>?</li>
    <li>What is <strong>featureC</strong>?</li>
  </ul>
</li>
<li><h3>elements-to-feature</h3>
<p>
elements-to-features conversation means that users know the elements regarding the feature but ask whether that feature exist or not within the system. For example:</p>
<ul>
  <li>Which <strong>features</strong> have <strong>product entity</strong>?</li>
  <li>Do we have a <strong>feature</strong> where it <strong>describes the total sum of this month revenue</strong>?</li>
  <li>Do we have feature that has <strong>this SQL</strong>?</li>
</ul>
</li>
<li><h3>entity-to-elements</h3>
<p>
entity-to-elements conversation meanns that users <strong>know</strong> the entity name but seek information regarding that entity elements. For example:</p>
<ul>
  <li>What is the join key of <strong>entityA</strong>?</li>
  <li>What is <strong>entityB</strong>?</li>
  <li>Can you tell me the business logic of <strong>entityC</strong></li>
</ul>
</li>
<li><h3>elements-to-entity</h3>
<br>
elements-to-entity conversation means that users know the elements regarding the entity but ask whether that entity exist or not within the system. For example:
  <ul>
    <li>Which <strong>entity</strong> has <strong> customerID as it's Join key</strong>?</li>
    <li> Do we have <strong>entity</strong> that is described <strong>as an unique identifier for product</strong>?</li>
  </ul>
</li>

<h3>2. Feature Registrations</h3>
<img src="Diagram_sources\feature registration flowchart.png" alt="feature_registration_flowchart">
<br>
Feature Registration means that whenever users want to register a new feature into a system. For examples:
<ul>
<li>I want to register a feature</li>
<li>I want to register new feature</li>
<br>
There are necessary procedures that need to be checked for validations, and many steps for the registration execution
</ul>

<h2>System Inference</h2>
<img src="Diagram_sources\System Inference.png" alt="system_inference_graph">

<h2><a href="feature_search">Directory Explanatory</a></h2>
<h3>Folder Definitions</h3>

<li>
  <h4><a href = "feature_search/SQL_parser">SQL Parser</a></h4>
  <h4>This folder contains the SQL Parser code file, Embedder code, Testing code, and the Index for the SQL Structure and embeddings</h4>
  <h4>Parser Files:</h5>
  <ul>
 
  <li>
    <strong><a href="feature_search/SQL_parser/sql_field_index.py">sql_field_index.py</a></strong>
    <br>
    This file traces each feature's lineage and dependency,
    which is used to extract the structure of the SQL for each feature.
  </li>

  <li>
    <strong><a href="feature_search/SQL_parser/query_structure_extract.py">query_structure_extract.py</a></strong>
    <br>
    This file extracts the structure of each feature's SQL,
    which is used to reconstruct the SQL.
  </li>   

  <li>
      <strong><a href="feature_search/SQL_parser/sql_reconstructions.py">sql_reconstructions.py</a></strong>
      <br>
      This file reconstructs the SQL per feature using the extracted structure,
      where the used method is asking the LLM (gemini-3.5-flash-lite) to reconstruct the SQL via prompting.
      The reconstructed SQL will be used for vector embedding
  </li>  
  
  </ul>
  
  <h4>Vector Embedder File:</h5>
  <ul>
  <li>
    <strong><a href="feature_search/SQL_parser/embbed_sql.py">embbed_sql.py</a></strong>
    <br>
    This file embeds the reconstructed SQL per feature into vector embeddings
  </li>   
  </ul>

  <h4>Testing File:</h5>
  <ul>
  <li>
    <strong><a href="feature_search/SQL_parser/cases-test.py">cases-test.py</a></strong>
    <br>
    This file is to test whether the SQL tracer works correctly (Check whether the lineage is correct from the parser).
    It takes two parameters which are the tree (the parsed SQL) and the feature that wants to be traced
  </li>   
  </ul>

  <h4>SQL Index Files:</h5>
  <ul>
  <li>
    <strong><a href="feature_search/SQL_parser/NOTE.txt">field_sql_index.json</a></strong>
    <br>
    This file contains the lineage and the structure of each feature in form of indexing.
    The index will be used in feature-to-SQL (features to elements) conversation.
  </li>   

   <li>
    <strong><a href="feature_search/SQL_parser/NOTE.txt">reconstructed_sql.json</a></strong>
    <br>
    This file contains reconstructed SQL for each feature in form of indexing (The reconstructed SQL was generated by AI)
  </li>  

  <li>
    <strong><a href="feature_search/SQL_parser/NOTE.txt">sql_embeddings.json</a></strong>
    <br>
    This file contains the vector embeddings of the reconstructed SQL.
    The vector embeddings will be used in SQL-to-feature (elements to features) conversation.
  </li>  
  </ul>
        
  
</li>

<li>
  <h4><a href="feature_search/index_dictionary">Index Dictionary [Confidential] </a></h4>
  <p>This folder contains the index lists, which are used for searching features.</p>
  <h4>Index Files:</h4>
  <ul>
    <li><strong><a href="feature_search/index_dictionary/NOTE.txt">feature_index.json</a></strong>
      <br>
      This JSON file contains indexes for feature-view-related information
      such as the feature view name, time-to-live (TTL), entity, and feature name. This index is sued for
      <h4>Features-to-Elements Conversation</h4>
      <ul>
        <li>Feature View - Entity Conversation</li>
        <li>Feature View - Description Conversation</li>
        <li>Feature View - Feature Name Conversation</li>
        <li>Feature - Description Conversation</li>
        <li>Feature - Business Logic Conversation</li>
      </ul>
      <h4>Elements-to-Features Conversation</h4>
      <ul>
    <li>Entity - Feature View Conversation</li>
        <li>TTL - Feature View Conversation</li>
        <li>Feature Name - Feature View Conversation</li>
      </ul>
    </li>


  <li>
      <strong><a href="feature_search/index_dictionary/NOTE.txt"> entities_index.json</a></strong>
      <br>
      This JSON file contains indexes for entity-related information
      such as the entity name, join key, description, and business logic. This index is used for
      <h4>Entity-to-Elements Conversation</h4>
      <ul>
        <li>Entity - Join Key Conversation</li>
        <li>Entity - Description Conversation</li>
        <li>Entity - Business Logic Conversation</li>
      </ul>
  </li>
  
  <li>
      <strong><a href="feature_search/index_dictionary/NOTE.txt"> field_index.json</a></strong>
      <br>
      This JSON file contains indexes for feature related information
      such as the feature name, the entity of the feature, the data type, description, and business logic. This index is used for
      <h4>Feature Registration (Validation Step)</h4>
      <ul>
        <li>Check whether want-to-register feature: [feature_name,entity] exists in the system </li>
      </ul>
  </li>
  
  <li>
    <strong><a href="feature_search/index_dictionary/NOTE.txt"> feature_view_sql_structure_index.json</a></strong>
      <br>
      This JSON file contains the whole SQL structure for each YAML. This index is used for:
      <h4>Feature Registration (Writing Step) especially on editing existing YAML files</h4>
      <ul>
        <li>The SQL structure will be sent to the LLM to define ideas or changes within the existing YAML files</li>
      </ul>
  </li>

  <li>
      <strong><a href="feature_search/index_dictionary/NOTE.txt"> terminology_index.json</a></strong>
      <br>
      This JSON file contains indexes for company jargons or terminology. This index will be always used whenever users make queries. 
      <h4>Usage Implementation Examples:</h4> 
       <ul>
         <li>What is IDK Contract? -> What is IDK/I Don't Know Contract</li>
         <li>What is the YTD value of revenue? -> What is the YTD/Year-to-Date value of revenue? </li>
       </ul>
  </li>
  
  <li>
      <strong><a href="feature_search/index_dictionary/NOTE.txt"> unused_index Folder</a></strong>
      <br>
      This folder contains historical/legacy indexes which could be useful in future development. 
      <h4>File Explanations:</h4> 
       <ul>
         <li><a href =  "feature_search/index_dictionary/NOTE.txt">entities_description_embeddings.json</a>
         <br>
         This is the embedding file for entity, it embeds the entity description + business logic. The embeddings were migrated to 
         Open-source ChromaDB Vector Datatabase
         </li>
      </ul>
      <ul>
         <li><a href = "feature_search/index_dictionary/NOTE.txt">feature_semantic_index.json</a>
          <br>
          This file contains the embeddings of feature description + business logic. The index also contains useful metadata such as
          entity of the feature, the feature view, the business logic and description themselves. The embeddings were migrated to Open-source ChromaDB Vector Database
        </li>
      </ul>
      <ul>
        <li><a href = "feature_search/index_dictionary/NOTE.txt">feature_view_embeddings.json</a>
          <br>
          This file contains the embeddings of feature view description. The file is not used anymore due to lack of information that can  be easily processed or analyzed
        </li>
      </ul>
      <ul>
        <li><a href = "feature_search/index_dictionary/NOTE.txt">feature_view_embeddings_entity_based</a>
          <br>
          This file contains the embeddings of feature view description. The index was based on the entity for each feature view. The  file  is not used anymore due to lack of information that can be easily processed or analyzed
        </li>
      </ul>
      <ul>
        <li><a href = "feature_search/index_dictionary/NOTE.txt">field_embeddings.json</a>
          <br>
          This file contains the embeddings of feature description + business logic. The file is not used anymore due to lack of  information  that can be easily processed or analyzed
        </li>
      </ul>
  </li>
  </ul>
</li>



<li>
  <h4><a href = "feature_search/index_extraction">Index Extraction</a></h4>
  <p>This folder contains the code file for extracting indexes or embeddings</p>
  <h4>Index Extractor Files:</h4>
  <ul>
    <li><strong><a href="feature_search/index_extraction/extract_entities_index.py">extract_entities_index.py</a></strong>
      <br>
      This code file is used to extract entities information in form of indexes based on entity name. The index contains necessary entity information such as the join key / feature_field, the description, and the business logic. The indexID is based on the entity name, where the result is saved in <a href = "feature_search/index_dictionary/NOTE.txt">entities_index.json</a> file 
    </li>
    <li><strong><a href="feature_search/index_extraction/extract_features_index.py">extract_features_index.py</a></strong>
      <br>
      This code file is used to extract feature view information in form of indexes based on feature view name. The index contains necessary feature view information such as the entity, ttl(time-to-live),domain,confidentiality, and feature name. Specifically for feature view name and feature name, additional indexes were added which are the separated name rather than use '_' as the separator between words. The indexID is based on the feature view name, where the result is saved in <a href="feature_search/index_dictionary/NOTE.txt">feature_index.json</a> file 
    </li>
    <li><strong><a href="feature_search/index_extraction/extract_terminology.py">extract_terminology.py</a></strong>
      <br>
      This code file is used to extract companies terminology or jargons using the LLM agent. In this case gemini-3.5-flash-lite llm  model was used to extract the possible jargons. Later the extracted jargons will be normalized such as making it case insesitive, remove '_', etc, before being saved in  <a href ="feature_search/index_dictionary/NOTE.txt">terminology_index.json</a> file 
    </li>
    <li><strong><a href="feature_search/index_extraction/field_extractions.py">field_extractions.py</a></strong>
      <br>
      This code file is used to extract features information in form of indexes based on feature name. The index contains necessary feature information such as the type,description, and the business logic. The indexID is based on the feature name, where the result is saved in <a href = "feature_search/index_dictionary/NOTE.txt">field_index.json</a> file 
    </li>
    <li>
      <strong><a href="feature_search/index_extraction/extract_sql_for_edit_yaml.py">extract_sql_for_edit_yaml.py</a></strong>
      <br>
      This code file is used to extract YAML whole SQL structure using the SQLGlot parser. The result is saved in <a href = "feature_search/index_dictionary/NOTE.txt">feature_view_sql_structure_index.json</a> file 
    </li>
      <li>
      <strong><a href="feature_search/index_extraction/NOTE.txt"> unused_index_extractors Folder</a></strong>
      <br>
      This folder contains historical/legacy index extractors which could be useful in future development. 
      <h4>File Explanations:</h4> 
      <ul>
         <li><a href = "feature_search/index_extraction/NOTE.txt">extract_entity_embeddings.py</a>
         <br>
         This file embeds the entity description + business logic. The used embedding model was 'gemini-embedding-01' model. The extractor is no longer being used, since it has been migrated to open-source ChromaDB vector database
         </li>
      </ul>
      <ul>
         <li><a href = "feature_search/index_extraction/NOTE.txt">extract_feature_view_embeddings.py</a>
         <br>
         This file embeds the feature view description. The used embedding model was 'gemini-embedding-01' model. The index was created based on the entity of the feature view. The extractor is no longer being used, since it lacks of features or elements that can be easily analyzed or processed
         </li>
     </ul>
     <ul>
         <li><a href = "feature_search/index_extraction/NOTE.txt">extract_features_embeddings.py</a>
         <br>
        This file embeds the feature description + business logic. The index also contains useful metadata such as
          entity of the feature, the feature view, the business logic and description themselves. The index is not used anymore since, the process has been migrated to ChromaDB Vector Database
         </li>
    </ul>
    <ul>
         <li><a href = "feature_search/index_extraction/NOTE.txt">extract_field_embeddings</a>
         <br>
        This file embeds the feature description + business logic. The index is not used anymore since it lacks of features or elements that can be easily analyzed or processed
         </li>
    </ul>
    </li>
  </li>
</li>


<li>
  <h4><a href = "feature_search/function_tools">Feature Functions</a></h4>
   <h4>This folder contains the main features of the agents which include feature registration,feature information retrieval, and entitiy information retrieval</h4>
  <h4>Feature Information Retrieval:</h5>
  <ul>
  <li>
    <strong><a href="feature_search/function_tools/feature_to_elements">feature_to_elements Folder</a></strong>
    <br>
    This folder contains code files that are used by the agents for feature-to-elements conversation, there are three main files:
    <ul>
      <li>
        <strong><a href="feature_search/function_tools/feature_to_elements/feature_view_info.py">feature_view_info.py</a></strong>
        <br>
        This code provides function that will be used by the agent to retrieve feature view information such as entity, description, ttl, and features name. It uses  <strong><a href="feature_search/index_dictionary/NOTE.txt">feature_index.json</a>Index </strong> as its searching dictionary
        There are four types of 'modes' where LLM can choose and decide when running this function:
        <ul>
          <li>description: If users ask about feature view descriptions</li>
          <li>entity: If users ask about what entity does a feature view have</li>
          <li>ttl: If users ask about what is the ttl (time-to-live) of a feature view</li>
          <li>feature_fields: If users ask about which features exist in asked feature view</li>
        </ul>
      </li>
      <li>
        <strong><a href="feature_search/function_tools/feature_to_elements/feature_info.py">feature_info.py</a></strong>
        <br>
        This code provides function that will be used by the agent to retrieve feature information such as its description, business logic, and data type. It uses  <strong><a href="feature_search/index_dictionary/NOTE.txt">feature_index.json</a>Index </strong> as its searching dictionary
        There are four  types of 'modes' where LLM can choose and decide when running this function:
        <ul>
          <li>description: If users ask about feature descriptions</li>
          <li>business_logic: If users ask about the business logic of asked features</li>
          <li>type: If users ask about what is the data type of asked features</li>
          <li>all: If users ask detailed information of the asked features</li>
        </ul>
    </li>
    <li>
        <strong><a href="feature_search/function_tools/feature_to_elements/feature_sql.py">feature_sql.py</a></strong>
        <br>
        This code provides function that will be used by the agent to retrieve feature SQL. It uses  <strong><a href="feature_search/SQL_parser/NOTE.txt">field_sql_index.json</a>Index </strong> as its searching dictionary
        The agent will check through the index to get the SQL structure for the searched features, and will generate the SQL by using the structure it gets from the index
      Note: For future development, it will use <a href = "feature_search/SQL_parser/NOTE.txt">reconstructed_sql.json</a> as its searching index (After its validated)
    </li>
    </ul>
  </li>
  <li>
    <strong><a href="feature_search/function_tools/elements_to_features">elements_to_features Folder</a></strong>
    <br>
    This folder contains code files that are used by the agents for elements-to-features conversation, there are three main files:
    <ul>
      <li>
        <strong><a href="feature_search/function_tools/elements_to_features/by_feature_view_info.py">by_feature_view_info.py</a></strong>
        <br>
        This code provides function that will be used by the agent to search feature view by the elements such as ttl, description, entity, and feature fields. It uses  <strong><a href="feature_search/index_dictionary/NOTE.txt">feature_index.json</a>Index </strong> as its keyword searching dictionary and feature_views_descriptions chromaDB collection as its semantic searching dictionary which use cosine-similarity to check the similarity
        There are four types of 'modes' where LLM can choose and decide when running this function:
        <ul>
          <li>description: If users provide information in form of description text and ask whether that feature view exists or not</li>
          <li>entity: If users provide entities and ask which feature views use that entities</li>
          <li>ttl: If users provide ttl and ask which feature views has that ttl(s)</li>
          <li>feature_fields: If users provide features and ask which feature views store that features</li>
        </ul>
      </li>
      <li>
        <strong><a href="feature_search/function_tools/elements_to_features/by_feature_field_info.py">by_feature_field_info.py</a></strong>
        <br>
        This code provides function that will be used by the agent to search feature by the elements such as description and business logic. It uses feature_description_bl_collection chromaDB collection as its semantic searching dictionary. 
    </li>
    <li>
        <strong><a href="feature_search/function_tools/elements_to_features/by_feature_field_sql.py">by_feature_field_sql.py</a></strong>
        <br>
        This code provides function that finds similarity between the user given query SQL with the vector embeddings. It uses  <strong><a href="feature_search/SQL_parser/NOTE.txt">sql_embeddings.json</a>Index </strong> as its semantic searching dictionary.
        The agent will check using cosine-similarity to check whether similar feature SQL exists
      Note: For future development, it will use sql_embeddings_collection ChromaDB Collection as its searching index (After its validated)
    </li>
    </ul>
  </li>
   <li>
    <strong><a href="feature_search/function_tools/entity_information">entity_information Folder</a></strong>
    <br>
    This folder contains code files that are used by the agents for entities-to-elements conversation, there are two main files:
    <ul>
      <li>
        <strong><a href="feature_search/function_tools/entity_information/entity_to_elements.py">entity_to_elements.py</a></strong>
        <br>
        This code provides function that will be used by the agent to retrieve entity information such as the join key, description, and business logic. It uses  <strong><a href="feature_search/index_dictionary/NOTE.txt">entities_index.json</a>Index </strong> as its keyword searching dictionary.
        There are four types of 'modes' where LLM can choose and decide when running this function:
        <ul>
          <li>description: If users ask about feature descriptions</li>
          <li>business_logic: If users ask about the business logic of asked features</li>
          <li>type: If users ask about what is the data type of asked features</li>
          <li>field_name: If users ask what is the join key of asked entities</li>
        </ul>
      </li>
      <li>
        <strong><a href="feature_search/function_tools/entity_information/elements_to_entity.py">elements_to_entity.py</a></strong>
        <br>
        This code provides function that will be used by the agent to search entities by the elements such as description, business logic, and join key. It uses entities_description_bl_collection chromaDB collection as its semantic searching dictionary and <strong><a href = "feature_search/index_dictionary/NOTE.txt">field_index.json</a></strong> Index as its keyword searching dictionary. 
         There are three types of 'modes' where LLM can choose and decide when running this function:
        <ul>
          <li>type: If users provide the data types and ask which entities have provided datatype</li>
          <li>description: If users provide description /  business logic to check whether similar entities exist or not</li>
          <li>field: If users provide the join key and ask which entities have provided join key</li>
        </ul>
    </li>
    </ul>
  </li>
  <li>
    <strong><a href="feature_search/function_tools/feature_registrations">feature_registrations Folder</a></strong>
    <br>
    This folder contains code files that are used by the agents for feature registration, there are two steps of feature registrations:
    <ul>
      <li><a href = "feature_search/function_tools/feature_registrations/validations">validations</a>
        <br>
        In validation, there are four main steps before getting to writing step:
        <ul>
          <li><a href ="feature_search/function_tools/feature_registrations/validations/validate_parameters.py">validate_parameters.py</a> : Check whether all necessary parameters exist in user query</li>
          <li><a href ="feature_search/function_tools/feature_registrations/validations/validate_entity.py">validate_entity.py</a> : Check whether if the entity exists in the system</li>
          <li><a href ="feature_search/function_tools/feature_registrations/validations/validate_feature_keyword.py">validate_feature_keyword.py</a> : Check whether the [feature_name,entity] already exist in the system to prevent duplicate value</li>
          <li><a href = "feature_search/function_tools/feature_registrations/validations/validate_feature_embeddings.py">validate_feature_embeddings.py</a> : Check whether there are similar features semantically with want-to-register-feature</li>
        </ul>
      </li>
      <li><a href = "feature_search/function_tools/feature_registrations/writing">writing</a></li>
      <br>
      In writing, there are two options:
      <ul>
        <li>Write New YAML : If entity does not have any YAML files or users choose to make new YAML
            <ul>
                  <li><a href = "feature_search/function_tools/feature_registrations/writing/write_new_feature_view.py">write_new_feature_view.py</a> : Write new YAML file which requires additional parameters such as feature view name, source type, tags, and discriptions</li>
            </ul>
        </li>
        <li>
            Write Existing YAML: If users choose to write new feature in existing YAML
          <ul>
            <li><a href = "feature_search/function_tools/feature_registrations/writing/write_feature_field_existing_yaml.py">write_feature_field_existing_yaml.py</a> : Add the new feature to the existing YAML, including the description and business logic</li>
            <li><a href = "feature_search/function_tools/feature_registrations/writing/sql_edit_planner.py">sql_edit_planner.py</a> : LLM will decide how to change the SQL structure (LLM will return a change plan). Uses <a href = "feature_search/index_dictionary/NOTE.txt">feature_view_sql_structure_index.json</a> index</li>
            <li><a href = "feature_search/function_tools/feature_registrations/writing/write_sql_existing_yaml.py">write_sql_existing_yaml.py</a> : Python will receive the change plan, then execute it to change the SQL in the YAML</li>
          </ul>
        </li>
      </ul>
  </li>
  </ul>
</li>
<li><a href = "feature_search/function_tools/global_function">global_function Folder</a>
<br>
This folder contains functions that are reused in many code files:
<ul>
  <li><a href = "feature_search/function_tools/terminology_check.py">terminology_check.py</a> : Provides the function to check terminology in user query. Uses <a href = "feature_search/index_dictionary/NOTE.txt">terminology_index.json</a>index</li>
  <li><a href = "feature_search/function_tools/global_function/cosine_similarity.py">cosine_similarity.py</a> : To calculate similarity between vectors. <strong> Not used anymore since ChromaDB provides the calculation</strong></li>
  <li><a href = "feature_search/function_tools/global_function/read_json.py">read_json.py</a> : To read json file (index files)</li>
</ul>
</li>


    
<li>
  <h4><a href = "feature_search/chromadb">Vector Embeddings</a></h4>
  <br>
  This folder contains the code files for embedding vectors to ChromaDB Vector Database, and the vector itself in form of collection
  There are four main functions and two additional files for testing files.
  <ul>
    <li>Main Functions:
    <ul>
      <li><a href = "feature_search/chromadb/feature_view_description_collection.py">feature_view_description_collection.py</a> : Embeds the feature view description and saved in <strong>feature_views_descriptions</strong> ChromaDB Collection</li>
      <li><a href = "feature_search/chromadb/feature_descriptions_bl_collection.py">feature_descriptions_bl_collection.py</a> : Embeds the feature description + business logic and saved in <strong>feature_description_bl_collection</strong> ChromaDB Collection</li>
      <li><a href = "feature_search/chromadb/entitiy_description_bl_collection.py">entitiy_description_bl_collection.py</a> : Embeds the entity description + business logic and saved in <strong>entities_description_bl_collection</strong> ChromaDB Collection</li>
      <li><a href = "feature_search/chromadb/feature_sql_semantic_collection.py">feature_sql_semantic_collection.py</a> : Embeds the re-constructed SQL and saved in <strong>sql_embeddings_collection</strong>ChromaDB Collection <strong>Note: This file has not been ran, hence the collection has not existed yet</strong> </li>
    </ul>
    </li>
  </ul>
</li>
<li>
  <h4><a href = "feature_search/yaml_list/NOTE.txt">YAML Files</a> : This folder contains the existing feature view YAML Files (The semantic layer) [Confidential]</h4>
</li>
<li>
  <h4><a href = "feature_search/entities/NOTE.txt">Entity Files</a> : This folder contains the existing entity/dimension YAML Files [Confidential]</h4>


</li>



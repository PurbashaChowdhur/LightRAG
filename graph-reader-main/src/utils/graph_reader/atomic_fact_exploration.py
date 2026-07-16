import ast
import re
from typing import List, Dict
from langchain_neo4j import Neo4jGraph

def get_atomic_facts_embedding_question(db:Neo4jGraph, 
                                        embedding_question:List[float], 
                                        key_elements:List[str], 
                                        embedding_model:str, 
                                        threshold:float) -> List[Dict[str, str]]:
    """
    Retrieves the AtomicFact content and corresponding Chunk ID considering the AtomicFacts that are most relevant to the input question.

    Args:
    - db: The Neo4jGraph object for querying the graph database.
    - embedding_question: The embedding of the question.
    - key_elements: A list of KeyElement strings.
    - embedding_model: The embedding model to use for similarity calculation.
    - threshold: The cosine similarity threshold.

    Returns:
    - A list of dictionaries containing the Chunk ID and AtomicFact text.
    """

    data = db.query(f"""
                    WITH {embedding_question} AS input_embedding, {threshold} AS threshold
                    MATCH (chunk:Chunk)-[:HAS_ATOMIC_FACT]->(fact:AtomicFact)-[:HAS_KEY_ELEMENT]->(k:KeyElement)
                    WHERE k.content IN {key_elements}
                    WITH chunk, fact, k, gds.similarity.cosine(input_embedding, fact.embedding_{embedding_model}) AS cosine_similarity
                    WHERE cosine_similarity >= threshold
                    RETURN DISTINCT fact.id as atomic_fact_id, fact.content AS text, chunk.id AS chunk_id
                    """)
    
    return data

def get_atomic_facts_all(db:Neo4jGraph, 
                         key_elements: List[str]) -> List[Dict[str, str]]:
    """
    Retrieves AtomicFact content and Chunk ID related to the given KeyElement list.

    Args:
    - db: The Neo4jGraph object for querying the graph database.
    - key_elements: A list of KeyElement strings.

    Returns:
    - A list of dictionaries containing the Chunk ID and AtomicFact text.
    """
     
    data = db.query(f"""
                    MATCH (chunk:Chunk)-[:HAS_ATOMIC_FACT]->(fact:AtomicFact)-[:HAS_KEY_ELEMENT]->(k:KeyElement)
                    WHERE k.content IN {key_elements}
                    RETURN DISTINCT fact.id as atomic_fact_id, fact.content AS text, chunk.id AS chunk_id
                    """)
    
    return data

def retrieve_related_recitals(db:Neo4jGraph, 
                              embedding_question:List[float], 
                              k_related_recitals:int, 
                              embedding_model:str) -> List[str]:
    
    data = db.query(f"""
                    CALL db.index.vector.queryNodes('RecitalChunk_{embedding_model}', {k_related_recitals}, $input_embedding)
                    YIELD node as recital, score
                    MATCH (recital)
                    RETURN recital.id as id
                    ORDER BY score DESC
                    """, 
                    params={"input_embedding": embedding_question})
    
    return [elem['id'] for elem in data]

def parse_function(input_str:str) -> Dict | None:
    """
    Parse the function name and arguments from the input string.

    Args:
    - input_str: The input string containing the function name and arguments.

    Returns:
    - A dictionary containing the function name and arguments.
    """

    pattern = r'(\w+)(?:\((.*)\))?'
    
    match = re.match(pattern, input_str)
    if match:
        function_name = match.group(1)  
        raw_arguments = match.group(2)      
        arguments = []
        if raw_arguments:
            try:
                parsed_args = ast.literal_eval(f'({raw_arguments})')  
                arguments = list(parsed_args) if isinstance(parsed_args, tuple) else [parsed_args]
            except (ValueError, SyntaxError):
                arguments = [raw_arguments.strip()]
        
        return {
            'function_name': function_name,
            'arguments': arguments
        }
    else:
        return None
    
def get_neighbors_by_key_element(db:Neo4jGraph, 
                                 key_elements:List[str]) -> List[str]:
    """
    Retrieves neighboring KeyElements based on the given KeyElement node.

    Args:
    - db: The Neo4jGraph object for querying the graph database.
    - key_elements: A list of KeyElement strings.

    Returns:
    - A list of neighboring KeyElements.
    """

    data = db.query(f"""
                    MATCH (k:KeyElement)<-[:HAS_KEY_ELEMENT]-(:AtomicFact)-[:HAS_KEY_ELEMENT]->(neighbor:KeyElement)
                    WHERE k.content IN {key_elements} AND NOT neighbor.content IN {key_elements}
                    WITH neighbor, count(*) AS count
                    ORDER BY count DESC LIMIT 50
                    RETURN collect(neighbor.content) AS possible_candidates
                    """)
    return data
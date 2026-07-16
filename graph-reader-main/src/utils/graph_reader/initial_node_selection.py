from typing import List
from langchain_neo4j import Neo4jGraph

def retrieve_potential_nodes(db:Neo4jGraph, 
                             embedding_question:List[float], 
                             k_potential_nodes:int, 
                             embedding_model:str) -> List[str]:
    """
    Retrieves the potential nodes that are most similar to the input question.

    Args:
    - db: The Neo4jGraph object.
    - embedding_question: The embedding of the input question.
    - k_potential_nodes: The number of potential nodes to retrieve.
    - embedding_model: The embedding model used.

    Returns:
    - A list of potential KeyElement nodes.
    """
    
    data = db.query(f"""
                    CALL db.index.vector.queryNodes('KeyElement_{embedding_model}', {k_potential_nodes}, {embedding_question})
                    YIELD node as key_element, score
                    MATCH (key_element)
                    RETURN key_element.content as content
                    ORDER BY score DESC
                    """)
    
    return [el['content'] for el in data]

def retrieve_key_elements_question(chain_extraction_question, 
                                   question: str) -> List[str]:
    """
    Retrieves the key elements of the input question through an LLM invocation.

    Args:
    - chain_extraction_question: The ChainExtractionQuestion object.
    - question: The user's question.

    Returns:
    - A list of key elements of the input question.
    """

    key_elements = chain_extraction_question.invoke({"question": question})
    
    return key_elements.key_elements
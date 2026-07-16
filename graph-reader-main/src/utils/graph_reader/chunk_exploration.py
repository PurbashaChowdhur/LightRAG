from typing import List, Dict
from langchain_neo4j import Neo4jGraph
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from neo4j_database import *

def get_reference_chunks_annex(db:Neo4jGraph, 
                               chunk_id:str) -> List[str]:
    """
    Retrieves the Annex IDs that reference the given Chunk ID.

    Args:
    - db: The Neo4jGraph object for querying the graph database.
    - chunk_id: The Chunk ID.

    Returns:
    - A list of Chunk IDs of the Annex IDs that are referenced by the given Chunk ID.
    """

    data = []
    annexes = db.query(f"""
                    MATCH (c:Chunk)-[:HAS_REFERENCE]->(a:Annex)
                    WHERE c.id = '{chunk_id}' and a.id <> '1'
                    RETURN a.id as annex_id
                    """)
    if annexes == []:
        return data
    
    annexes_ids = [elem['annex_id'] for elem in annexes]

    for annex_id in annexes_ids:
        if has_sections_annex(db, annex_id):
            res = db.query("""
                            MATCH (a:Annex)-[:HAS_SECTION]->(s:Section)-[:HAS_CHUNK]->(c:Chunk)
                            WHERE a.id = $annex_id
                            RETURN c.id as chunk_id
                           """,
                           params = {'annex_id':annex_id})
        else:
            res = db.query("""
                            MATCH (a:Annex)-[:HAS_CHUNK]->(c:Chunk)
                            WHERE a.id = $annex_id
                            RETURN c.id as chunk_id
                           """,
                           params = {'annex_id':annex_id})
            
        res_list = [elem['chunk_id'] for elem in res]
        data = list(set(data + res_list))
        
    return data

def get_related_recitals_chunk(db:Neo4jGraph, 
                               chunk_id:str) -> List[str]:
    """
    Retrieves the Recital IDs that are related to the given Chunk ID.

    Args:
    - db: The Neo4jGraph object for querying the graph database.
    - chunk_id: The Chunk ID.

    Returns:
    - A list of Recital IDs that are related to the given Chunk ID.
    """

    data = db.query(f"""
                    MATCH (ca:Chunk)-[:HAS_RELATED_RECITAL]->(r:Recital)-[:HAS_CHUNK]->(cr:Chunk)
                    WHERE ca.id = '{chunk_id}'
                    RETURN cr.id as recital_id
                    """)
    
    if data == []:
        return data
    
    return [elem['recital_id'] for elem in data]

def get_related_recitals_article(db:Neo4jGraph, 
                                 article_id:str) -> List[str]:
    """
    Retrieves the Recital IDs that are related to the given Article ID.

    Args:
    - db: The Neo4jGraph object for querying the graph database.
    - article_id: The Article ID.

    Returns:
    - A list of Recital IDs that are related to the given Article ID.
    """

    data = db.query(f"""
                    MATCH (a:Article)-[:HAS_RELATED_RECITAL]->(r:Recital)-[:HAS_CHUNK]->(c:Chunk)
                    WHERE a.id = '{article_id}'
                    RETURN c.id as recital_id
                    """)
    
    if data == []:
        return data
    
    return [elem['recital_id'] for elem in data]

def get_chunk(db:Neo4jGraph, 
              chunk_id: str) -> List[Dict[str, str]]:
    """
    Retrieves the content of a Chunk based on the Chunk ID.

    Args:
    - db: The Neo4jGraph object for querying the graph database.
    - chunk_id: The ID of the Chunk to retrieve.

    Returns:
    - A list  containing the dictionary, Chunk ID and text content.
    """

    data = db.query(f"""
                    MATCH (c:Chunk)
                    WHERE c.id = '{chunk_id}'
                    RETURN c.id AS chunk_id, c.content AS text
                    """)
    return data

def get_subsequent_chunk_id(db:Neo4jGraph, 
                            chunk_id:str) -> List[Dict[str, str]]:
    """
    Retrieves the subsequent Chunk ID based on the current Chunk ID.

    Args:
    - db: The Neo4jGraph object for querying the graph database.
    - chunk_id: The current Chunk ID.

    Returns:
    - The subsequent Chunk ID.
    """
    data = db.query(f"""
                    MATCH (c:Chunk)-[:NEXT]->(next:Chunk)
                    WHERE c.id = {chunk_id}
                    RETURN next.id AS next
                    """)
    return data

def get_previous_chunk_id(db:Neo4jGraph, 
                          chunk_id:str) -> List[Dict[str, str]]:
    """
    Retrieves the previous Chunk ID based on the current Chunk ID.

    Args:
    - db: The Neo4jGraph object for querying the graph database.
    - chunk_id: The current Chunk ID.

    Returns:
    - The previous Chunk ID.
    """
    data = db.query(f"""
                    MATCH (c:Chunk)<-[:NEXT]-(previous:Chunk)
                    WHERE c.id = {chunk_id}
                    RETURN previous.id AS previous
                    """)
    return data

def get_articles_from_chunks(chunks:List[str]) -> List[str]:
    """
    Retrieves the Article IDs from the given list of Chunk IDs.

    Args:
    - chunks: A list of Chunk IDs.

    Returns:
    - A list of Article IDs.
    """

    article_numbers = set()
    for chunk in chunks:
        article_number = chunk.split('-')[0]
        article_numbers.add(article_number)
    
    return list(article_numbers)

def get_article_by_chunk_id(chunk_id:str) -> str:
    """
    Retrieves the Article ID from the given Chunk ID.

    Args:
    - chunk_id: str

    Returns:
    - str, the Article ID.
    """
    
    parts = chunk_id.split('-')
    return f"{parts[0]}"
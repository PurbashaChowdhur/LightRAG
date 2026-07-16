import os
from src.utils._io import *
from typing import List
from langchain_neo4j import Neo4jGraph

def has_sections(chapter_title:str) -> bool:
    """
    Evaluates whether a chapter has sections or not.

    Args:
    - chapter_title: str

    Returns:
    - bool, True if the chapter has sections, False otherwise.
    """
    current_dir = os.path.dirname(__file__)
    data_dir = os.path.join(os.path.dirname(current_dir), "data/ai act/chapters/")

    for i in range(1,14):
        file_path = os.path.join(data_dir, f'chapter_{i}.pkl')
        chapter = load_from_pkl(file_path)

        if chapter.chapter_title == chapter_title:
            return chapter.sections != []
        
def has_sections_annex(db:Neo4jGraph, annex_id:str) -> bool:
    """
    Evaluates whether an annex has sections or not.

    Args:
    - db: Neo4jGraph
    - annex_id: str

    Returns:
    - bool, True if the annex has sections, False otherwise.
    """
    res = db.query("""
                   MATCH (a:Annex)-[:HAS_SECTION]->(s:Section)
                   WHERE a.id = $annex_id
                   RETURN s.id as section_id
                   """,
                   params = {'annex_id':annex_id})
    
    res_list = [elem['section_id'] for elem in res]

    if res_list != []:
        return True
    return False

def add_node(label:str, properties:dict) -> str:
    """
    Add a node to the graph database. The node has a label and a set of properties.

    Args:
    - label: str - the label of the node.
    - properties: dict - the properties of the node.

    Returns:
    - str - the query to add the node to the graph database
    """

    property_assignments = ", ".join([f"{key}: ${key}" for key in properties.keys()])
    query = f"MERGE (n:{label} {{{property_assignments}}}) RETURN n"
    
    return query

def add_relationship_by_id(label_source:str, label_dest:str, label_rel:str, id_source:str, id_dest:str) -> str:
    """
    Add a relationship between two nodes in the graph database, according to their ids.

    Args:
    - label_source: str - the label of the first node.
    - label_dest: str - the label of the second node.
    - label_rel: str - the label of the relationship.
    - id_source: str - the id of the first node.
    - id_dest: str - the id of the second node.

    Returns:
    - str - the query to add the relationship between the two nodes.
    """

    query = (
        f"MATCH (a:{label_source}), (b:{label_dest}) "
        f"WHERE a.id = '{id_source}' AND b.id = '{id_dest}' "
        f"MERGE (a)-[r:{label_rel}]->(b)"
    )
    return query

def add_relationship_chunk_chunk(id_source:str, id_dest:str) -> str:
    """
    Add a relationship between two Chunk nodes in the graph database. The relationship is called [:NEXT].

    Args:
    - id_source: str - the id of the first chunk.
    - id_dest: str - the id of the second chunk.
    - chunk_number_source: str - the chunk number of the first chunk.
    - chunk_number_dest: str - the chunk number of the second chunk.

    Returns:
    - str - the query to add the relationship between the two chunks.
    """

    query = (
        "MATCH (a:Chunk), (b:Chunk)"
        f"WHERE a.id = '{id_source}' AND b.id = '{id_dest}' "
        "MERGE (a)-[:NEXT]->(b)"
    )
    return query 

def add_relationship_article_recital(article_id:str, related_recital_id:str):
    """
    Add a relationship between an Article and a Recital in the graph database. The relationship is called [:HAS_RELATED_RECITAL].

    Args:
    - article_id: str - the id of the article.
    - related_recital_id: str - the id of the related recital.

    Returns:
    - str - the query to add the relationship between the article and the recital.
    """

    query = (
            "MATCH (a:Article), (r:Recital) "
            f"WHERE a.id = '{article_id}' AND r.id = '{related_recital_id}' "
            "MERGE (a)-[:HAS_RELATED_RECITAL]->(r)"
    )

    return query

def add_relationship_chunk_recital(chunk_id:str, related_recital_id:str):
    """
    Add a relationship between a Chunk and a Recital in the graph database. The relationship is called [:HAS_RELATED_RECITAL].

    Args:
    - chunk_id: str - the id of the chunk.
    - related_recital_id: str - the id of the related recital.

    Returns:
    - str - the query to add the relationship between the chunk and the recital.
    """
    query = (
            "MATCH (c:Chunk), (r:Recital) "
            f"WHERE c.id = '{chunk_id}' AND r.id = '{related_recital_id}' "
            "MERGE (c)-[:HAS_RELATED_RECITAL]->(r)"
    )
    
    return query

def add_relationship_chunk_atomic_fact(chunk_id:str, chunk_number:str, atomic_fact_id:str) -> str:
    """
    Add a relationship between a Chunk and an AtomicFact in the graph database. The relationship is called [:HAS_ATOMIC_FACT].

    Args:
    - chunk_id: str - the id of the chunk.
    - chunk_number: str - the chunk number of the chunk.
    - atomic_fact_id: str - the id of the atomic fact.

    Returns:
    - str - the query to add the relationship between the chunk and the atomic fact.
    """

    query = (
        "MATCH (a:Chunk), (b:AtomicFact) "
        f"WHERE a.id = '{chunk_id}' AND a.chunk_number = '{chunk_number}' AND b.id = '{atomic_fact_id}' "
        f"MERGE (a)-[r:HAS_ATOMIC_FACT]->(b)"
    )
    return query

def check_key_elements(embedding:List[float]) -> str:
    """
    Return KeyElement nodes in the graph database that have an embedding similar to the input embedding.

    Args:
    - embedding: List[float] - the embedding of the KeyElement.

    Returns:
    - str - the query to return the KeyElement nodes with similar embeddings.
    """
    query = f"""
            MATCH (k:KeyElement)
            WHERE k.embedding IS NOT NULL AND gds.similarity.cosine({embedding}, k.embedding) > 0.8
            RETURN k.content AS key_element
            """ 
    
    return query

def add_relationship_atomic_fact_key_elements(atomic_fact_id:str, key_element:str) -> str:
    """
    Add a relationship between an AtomicFact and a KeyElement in the graph database. The relationship is called [:HAS_KEY_ELEMENT].

    Args:
    - atomic_fact_id: str - the id of the atomic fact.
    - key_element: str - the content of the KeyElement.

    Returns:
    - str - the query to add the relationship between the atomic fact and the key element
    """

    query = (
        "MATCH (a:AtomicFact), (b:KeyElement) "
        f"WHERE a.id = '{atomic_fact_id}' AND b.content = \"{key_element}\" " 
        f"MERGE (a)-[r:HAS_KEY_ELEMENT]->(b)"
    )
    return query

def check_db_correctness() -> list[str]:
    """
    Checks whether the graph database is correctly populated. The following checks are performed:
    
    1. Check if all articles are connected to some chapters or to some sections;
    2. Check if all sections are connected to some chapters;
    3. Check if all chapters are connected to some sections or some articles;
    4. Check if all chunks are connected to some articles;
    5. Check if all atomic facts are connected to some chunks;
    6. Check if all key elements are connected to some atomic facts;
    7. Check if all annexes are connected to some chunks or sections;
    8. Check if all sections of annexes have chunks;
    9. Check if all articles have the entry into force date;
    10. Check if all AtomicFact nodes have the embedding property.
    11. Check if all KeyElement nodes have the embedding property.

    Returns:
    - List[str] - the list of queries to check the correctness of the database.
    """

    queries = []
    queries.append("""
                   MATCH (a:Article) 
                   WHERE NOT (:Section)-[:HAS_ARTICLE]->(a) AND NOT (:Chapter)-[:HAS_ARTICLE]->(a)
                   RETURN a
                   """)
    
    queries.append("""
                    MATCH (s:Section) 
                    WHERE NOT s.id CONTAINS 'Annex' AND NOT (:Chapter)-[:HAS_SECTION]->(s)
                    RETURN s
                    """)
    
    queries.append("""
                    MATCH (c:Chapter) 
                    WHERE NOT (c)-[:HAS_SECTION]->(:Section) AND NOT (c)-[:HAS_ARTICLE]->(:Article)
                    RETURN c
                    """)
    
    queries.append("""
                    MATCH (c:Chunk) 
                    WHERE NOT c.id CONTAINS 'Annex' AND NOT (:Article)-[:HAS_CHUNK]->(c)
                    RETURN c
                    """)
    
    queries.append("""
                    MATCH (a:AtomicFact) 
                    WHERE NOT (:Chunk)-[:HAS_ATOMIC_FACT]->(a)
                    RETURN a
                    """)
    
    queries.append("""
                    MATCH (k:KeyElement) 
                    WHERE NOT (:AtomicFact)-[:HAS_KEY_ELEMENT]->(k)
                    RETURN k
                    """)
        
    queries.append("""
                    MATCH (an:Annex) 
                    WHERE NOT (an)-[:HAS_CHUNK]->(:Chunk) AND NOT (an)-[:HAS_SECTION]->(:Section)
                    RETURN an
                    """)
    
    queries.append("""
                    MATCH (s:Section) 
                    WHERE s.id CONTAINS 'Annex' AND NOT (s)-[:HAS_CHUNK]->(:Chunk)
                    RETURN s
                    """)
    
    queries.append("""
                    MATCH (a:Article) 
                    WHERE a.entry_into_force IS NULL
                    RETURN a
                    """)
    
    queries.append("""
                    MATCH (a:AtomicFact) 
                    WHERE a.embedding_GPT IS NULL
                    RETURN a
                    """)
    
    queries.append("""
                    MATCH (a:AtomicFact) 
                    WHERE a.embedding_LegalBERT IS NULL
                    RETURN a
                    """)
    
    queries.append("""
                    MATCH (k:KeyElement) 
                    WHERE k.embedding_LegalBERT IS NULL
                    RETURN k
                    """)
    
    queries.append("""
                    MATCH (k:KeyElement) 
                    WHERE k.embedding_GPT IS NULL
                    RETURN k
                    """)

    return queries
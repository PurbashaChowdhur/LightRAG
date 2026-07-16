from typing import List
from pydantic import BaseModel, Field

class AtomicFact(BaseModel):
    """
    Class that represents an AtomicFact object. Each AtomicFact object has the following attributes:
    - atomic_fact: str - the smallest, indivisible facts, presented as concise sentences.
    - key_elements: List[str] - the essential nouns, verbs, and adjectives that are pivotal to the atomic fact's
    """
    atomic_fact: str = Field(description = """The smallest, indivisible facts, presented as concise sentences. These include propositions, theories, existences, concepts, and implicit elements like logic, causality, event sequences, interpersonal relationships, timelines, etc.""")
    
    key_elements: List[str] = Field(description = """The essential nouns (e.g., characters, times, events, places, numbers), verbs (e.g.,actions), and adjectives (e.g., states, feelings) that are pivotal to the atomic fact's narrative.""")

class Extraction(BaseModel):
    """
    Class that represents the output of the AtomicFact and KeyElement extraction. It contains the following attributes:
    - atomic_facts: List[AtomicFact] - the list of atomic facts extracted from the text.
    """
    atomic_facts: List[AtomicFact] = Field(description = "List of atomic facts")
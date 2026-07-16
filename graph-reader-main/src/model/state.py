from typing_extensions import TypedDict
from typing import List, Annotated
from operator import add

class InputState(TypedDict):
    """
    Input state of the agent.

    Fields:
    - question: A string that stores the user's question.
    """
    question: str

class OutputState(TypedDict):
    """
    Output state of the agent.

    Fields:
    - answer: A string containing the agent's answer to the question.
    - previous_actions: A list of strings that logs the actions the agent has taken so far.
    - visited_chunks: A list of strings that stores the chunks the agent has visited.
    - relevant_chunks: A list of strings that stores the chunks the agent has identified as relevant.
    - relevant_recitals: A list of strings that stores the recitals the agent has identified as relevant.
    - visited_atomic_facts: A list of strings that stores the atomic facts the agent has visited.
    - visited_key_elements: A list of strings that stores the key elements the agent has visited.
    """
    answer: str
    previous_actions: List[str]
    selected_key_elements: List[str]
    selected_atomic_facts: List[str]
    visited_chunks: List[str]
    references: dict[str, List[str]]
    time: float

class OverallState(TypedDict):
    """
    Represents a more comprehensive state for the agent, encapsulating the entire workflow or reasoning process.

    Fields:
    - question: The user's question, similar to InputState.
    - rational_plan: A string detailing the high-level plan or reasoning strategy.
    - notebook: A string acting as a workspace for intermediate notes or observations.
    - previous_actions: A list of strings, similar to OutputState, but includes an annotation, Annotated[List[str], add], to add additional metadata or processing functionality (e.g., dynamically appending actions).
    - check_atomic_facts_queue: A list of strings representing a queue for verifying AtomicFact.
    - check_chunks_queue: A list of strings representing a queue for analyzing Chunk.
    - neighbor_check_queue: A list of strings representing a queue for examining neighboring or related data.
    - chosen_action: A string describing the action currently being executed or selected.
    - visited_chunks: A list of strings representing the chunks visited during the reasoning process.
    - relevant_chunks: A list of strings representing the chunks identified as relevant or important.
    - relevant_recitals: A list of strings representing the recitals deemed relevant during the reasoning process.
    - visited_atomic_facts: A list of strings representing the atomic facts visited during the reasoning process.
    - visited_key_elements: A list of strings representing the key elements visited during the reasoning process.
    """
    question: str
    rational_plan: str
    notebook: str
    previous_actions: Annotated[List[str], add]
    check_atomic_facts_queue: List[str]
    check_chunks_queue: List[str]
    neighbor_check_queue: List[str]
    chosen_action: str
    selected_key_elements: List[str]
    selected_atomic_facts: List[str]
    visited_chunks: List[str]
    relevant_atomic_facts: List[str]
    relevant_chunks: List[str]
    relevant_recitals: List[str]
    references: dict[str, List[str]]
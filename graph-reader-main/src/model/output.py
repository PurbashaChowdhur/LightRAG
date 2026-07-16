from pydantic import BaseModel, Field
from typing import List

class ExtractionQuestion(BaseModel):
    """
    Represents the output of the KeyElement extraction from the question.

    Attributes:
    - key_elements: List[str] -- The essential nouns, verbs, and adjectives that are central to the question's content.
    """
    
    key_elements: List[str] = Field(description = """The essential nouns (e.g., characters, times, events, places, numbers), verbs (e.g.,actions), and adjectives (e.g., states, feelings) that are central to the question's content.""")

class Node(BaseModel):
    """
    Represents the structure of each element in the InitialNodes output.

    Attributes:
    - key_element: str -- KeyElement
    - score: int -- Relevance of the KeyElement to the question and rational plan as score between 0 and 100. A score of 100 implies a high likelihood of relevance to the question and rational plan, whereas a score of 0 suggests minimal relevance.
    """
    
    key_element: str = Field(description="""KeyElement""")
    
    score: int = Field(description="""Relevance of the KeyElement to the question and rational plan as score between 0 and 100. A score of 100 implies a high likelihood of relevance to the question and rational plan, whereas a score of 0 suggests minimal relevance.""")

class InitialNodes(BaseModel):
    """
    Represents the output of the Initial Node Selection phase.

    Attributes:
    - key_element_nodes: List[Node] -- List of KeyElement nodes and their relevance scores to the question and rational plan.
    """
    
    key_element_nodes: List[Node] = Field(description="List of KeyElement nodes and their relevance scores to the question and rational plan")

class AtomicFactOutput(BaseModel):
    """
    Represents the output of the Atomic Fact Exploration phase.

    Attributes:
    - updated_notebook: str 
    - rational_next_action: str 
    - chosen_action: str 
    - relevant_atomic_facts: List[str] 
    """
    
    updated_notebook: str = Field(description="Updated version of the input notebook with new insights and findings about the question retrieved by reading the input AtomicFact nodes. Notice that the notebook should be updated only considering relevant AtomicFacts, and it should only contain an articulate text. For each new finding, indicate the AtomicFact node from which it was derived.")
    
    rational_next_action: str = Field(description="The rational explanation for the chosen Action.")
    
    chosen_action: str = Field(description="""read_chunk(List[ID]) or stop_and_read_neighbor(). (Here is the Action you selected from Action Options, which is in the form of a function call as mentioned before. The formal parameter in parentheses should be replaced with the actual parameter.)""")

    relevant_atomic_facts: List[str] = Field(description="List of IDs of AtomicFact nodes that are relevant to the question and plan. Specifically, this list must contain all the IDs of the AtomicFact nodes that were used for updating the notebook.")


class ChunkOutput(BaseModel):
    """
    Represents the output of the Chunk Exploration phase.

    Attributes:
    - updated_notebook: str
    - rational_next_move: str 
    - chosen_action: str 
    - relevant_chunk: bool
    """
    
    updated_notebook: str = Field(description="Updated version of the input notebook with new insights and findings about the question retrieved by reading the input text Chunk and Recital(s), if present. Notice that the notebook should be updated only if the current Chunk or Recital is relevant w.r.t. both the question and the rational plan, and it should only contain an articulate text, without lists of chunks. For each new finding, indicate the Chunk or Recital from which it was derived.")
    
    rational_next_move: str = Field(description="The rational explanation for the chosen Action.")  

    chosen_action: str = Field(description="search_more() or read_previous_chunk() or read_subsequent_chunk() or termination(). (Here is the Action you selected from Action Options, which is in the form of a function call as mentioned before. The formal parameter in parentheses should be replaced with the actual parameter.)")
  
    relevant_chunk: bool = Field(description="True if the Chunk is relevant to the question and plan, False otherwise. Specifically, if the Chunk was used for updating the notebook, it has to be considered relevant, otherwise it is irrelevant.")

class AllChunksOutput(BaseModel):
    """
    Represents the output of the All Chunks Exploration phase.

    Attributes:
    - updated_notebook: str  
    - search_more: bool 
    - relevant_chunk: bool 
    """

    updated_notebook: str = Field(description="Updated version of the input notebook with new insights and findings about the question retrieved by reading the input text Chunk and Recital(s), if present. Notice that the notebook should be updated only if the current Chunk or Recital is relevant w.r.t. both the question and the rational plan, and it should only contain an articulate text, without lists of chunks. For each new finding, indicate the Chunk or Recital from which it was derived.")

    search_more: bool = Field(description="True if the agent should search for more Chunks and recitals, False otherwise.")

    relevant_chunk: bool = Field(description="True if the Chunk is relevant to the question and plan, False otherwise. Specifically, if the Chunk was used for updating the notebook, it has to be considered relevant, otherwise it is irrelevant.")

class GenerateQuestionFromRational(BaseModel):
    """
    Represents the output of the Question Generation phase.

    Attributes:
    - generated_question: str -- The new question based on the rational plan, the notebook content and the input question.
    """

    generated_question: str = Field(description="""The new question based on the rational plan, the notebook content and the input question.""")

class NeighborOutput(BaseModel):
    """
    Represents the output of the Neighbor Exploration phase.

    Attributes:
    - rational_next_move: str -- The rational explanation for the chosen Action.
    - chosen_action: str -- read_neighbor_node() or termination(). (Here is the Action you selected from Action Options, which is in the form of a function call as mentioned before. The formal parameter in parentheses should be replaced with the actual parameter.)
    """

    rational_next_move: str = Field(description="""Rational explanation for the chosen Action.""")
    
    chosen_action: str = Field(description="""read_neighbor_node() or termination(). (Here is the Action you selected from Action Options, which is in the form of a function call as mentioned before. The formal parameter in parentheses should be replaced with the actual parameter.)""")

class AnswerGenerationOutput(BaseModel):
    """
    Represents the output of the Answer Generation phase.

    Attributes:
    - final_answer: str -- Answer to the input question, considering all the information contained in the iput notebook. Provide a structured
    """    
    
    final_answer: str = Field(description="""Answer to the input question, considering all the information contained in the iput notebook. Provide a structured answer.""")
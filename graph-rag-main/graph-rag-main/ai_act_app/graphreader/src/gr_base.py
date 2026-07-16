import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings.global_variables import *
from settings.prompts import *
from src.utils._io import *
from src.utils.general_utils import *
from src.datamodule.gr_base import *
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
import datetime
import logging

class GraphReaderBase:
    def __init__(self, args):
        logging.basicConfig(level=logging.INFO)

        db = Neo4jGraph(
            url = args["neo4j_uri"], 
            username = args["neo4j_username"], 
            password = args["neo4j_password"],
            database=args["neo4j_database"],
        )

        self.embedding_openai = OpenAIEmbeddings(
            model = EMBEDDING_OPENAI,
            api_key = OPENAI_API_KEY,
            dimensions = EMBEDDING_DIMENSION
        )

        gpt = ChatOpenAI(
            model = MODEL,
            api_key = OPENAI_API_KEY
        )

        # Phases
        self.rational_plan_creation_base = Phase("rational_plan_creation_base",
                                        gpt, 
                                        ChatPromptTemplate.from_messages(
                                                                [
                                                                    (
                                                                        "system",
                                                                        rational_plan_base,
                                                                    ),
                                                                    (
                                                                        "human",
                                                                        (
                                                                            "Question: {question}"
                                                                        ),
                                                                    ),
                                                                ]
                                                            ),
                                        StrOutputParser())

        self.extraction_question = Phase("extraction_question",
                                gpt.with_structured_output(ExtractionQuestion), 
                                ChatPromptTemplate.from_messages(
                                                            [
                                                                (
                                                                    "system",
                                                                    key_element_question_extraction,
                                                                ),
                                                                (
                                                                    "human",
                                                                    (
                                                                    "Question: {question}"
                                                                    ),
                                                                ),
                                                            ]
                                ))

        self.initial_node_selection = Phase("initial_node_selection",
                                    gpt.with_structured_output(InitialNodes), 
                                    ChatPromptTemplate.from_messages(
                                                            [
                                                            (
                                                                "system",
                                                                initial_node,
                                                            ),
                                                            (
                                                                "human",
                                                                (
                                                                    """
                                                                    Question: {question}
                                                                    Rational plan: {rational_plan}
                                                                    KeyElement nodes: {nodes}
                                                                    """
                                                                ),
                                                            ),
                                                        ]
                                    ))
        
        self.atomic_fact_exploration = Phase("atomic_fact_exploration",
                                    gpt.with_structured_output(AtomicFactOutput), 
                                    ChatPromptTemplate.from_messages(
                                                        [
                                                            (
                                                                "system",
                                                                exploring_atomic_facts,
                                                            ),
                                                            (
                                                                "human",
                                                                (
                                                                    """
                                                                    Question: {question}
                                                                    Rational plan: {rational_plan}
                                                                    Notebook: {notebook}
                                                                    Atomic facts: {atomic_facts}
                                                                    """
                                                                ),
                                                            ),
                                                        ]
                                    ))
        
        self.chunk_exploration = Phase("chunk_exploration",
                                gpt.with_structured_output(ChunkOutput), 
                                ChatPromptTemplate.from_messages(
                                                            [
                                                                (
                                                                    "system",
                                                                    exploring_all_chunks_recital,
                                                                ),
                                                                (
                                                                    "human",
                                                                    (
                                                                        """
                                                                        Question: {question}
                                                                        Rational plan: {rational_plan}
                                                                        Previous actions: {previous_actions}
                                                                        Notebook: {notebook}
                                                                        Chunk: {chunk}
                                                                        """
                                                                    ),
                                                                ),
                                                            ]
                                )
                            )
        
        self.all_chunks_exploration = Phase("all_chunks_exploration",
                                gpt.with_structured_output(AllChunksOutput), 
                                ChatPromptTemplate.from_messages(
                                                            [
                                                                (
                                                                    "system",
                                                                    exploring_all_chunks_recital,
                                                                ),
                                                                (
                                                                    "human",
                                                                    (
                                                                        """
                                                                        Question: {question}
                                                                        Rational plan: {rational_plan}
                                                                        Previous actions: {previous_actions}
                                                                        Notebook: {notebook}
                                                                        Chunk: {chunk}
                                                                        """
                                                                    ),
                                                                ),
                                                            ]
                                )
                            )
        
        self.question_generation = Phase("question_generation",
                                gpt.with_structured_output(GenerateQuestionFromRational),
                                ChatPromptTemplate.from_messages(
                                                            [
                                                                (
                                                                    "system",
                                                                    generate_question_from_rational,
                                                                ),
                                                                (
                                                                    "human",
                                                                    (
                                                                        """
                                                                        Question: {question}
                                                                        Rational plan: {rational_plan}
                                                                        Notebook: {notebook}
                                                                        """
                                                                    ),
                                                                ),
                                                            ]
                                )
                            )
        
        self.neighbor_exploration = Phase("neighbor_exploration",
                                gpt.with_structured_output(NeighborOutput), 
                                ChatPromptTemplate.from_messages(
                                                            [
                                                                (
                                                                    "system",
                                                                    exploring_neighbors,
                                                                ),
                                                                (
                                                                    "human",
                                                                    (
                                                                        """
                                                                        Question: {question}
                                                                        Rational plan: {rational_plan}
                                                                        Notebook: {notebook}
                                                                        KeyElement nodes: {nodes}
                                                                        """
                                                                    ),
                                                                ),
                                                            ]
                                )
                            )
        
        self.answer_generation = Phase("answer_generation",
                            gpt.with_structured_output(AnswerGenerationOutput), 
                            ChatPromptTemplate.from_messages(
                                                        [
                                                            (
                                                                "system",
                                                                answer_generation_,
                                                            ),
                                                            (
                                                                "human",
                                                                (
                                                                    """
                                                                    Question: {question}
                                                                    Notebook: {notebook}
                                                                    """
                                                                ),
                                                            ),
                                                        ]
                            )
                        )

        # Config
        agent_config = {
            'logger': '',
            'db': db,
            'embedding_model': self.embedding_openai,
            'embedding_model_name' : 'GPT'
        }

        params = {
            'k_potential_nodes' : 50,
            'k_initial_nodes' : 15,
            'max_chunks' : 20,
        }

        self.__init_chain(agent_config=agent_config, params=params)

        
    def __init_chain(self, agent_config, params, ce_config="all_chunks"):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file, _ = create_directories(
            'logs/graph_reader_base/', ce_config, timestamp
        )

        logger = setup_logger(log_file, f"graph_reader_base {ce_config}")

        agent_config['logger'] = logger
        agent_config['embedding_model'] = self.embedding_openai
        agent_config['embedding_name'] = 'GPT'

        phases_config = {
            'rational_plan_creation': 'base',
            'initial_node_selection': 'question',
            'chunk_exploration': ce_config
        }

        gr = self.__build_graph_reader(agent_config, phases_config, params)
        langgraph = StateGraph(OverallState, input=InputState, output=OutputState)
        
        langgraph.add_node(gr.rational_plan_creation)
        langgraph.add_node(gr.initial_node_selection)
        langgraph.add_node(gr.atomic_fact_exploration)
        langgraph.add_node(gr.chunk_exploration)
        langgraph.add_node(gr.neighbor_exploration)
        langgraph.add_node(gr.answer_generation)

        langgraph.add_edge(START, "rational_plan_creation")
        langgraph.add_edge("rational_plan_creation", "initial_node_selection")
        langgraph.add_edge("initial_node_selection", "atomic_fact_exploration")

        langgraph.add_conditional_edges(
            "atomic_fact_exploration",
            gr.atomic_fact_condition,
        )

        langgraph.add_conditional_edges(
            "chunk_exploration",
            gr.chunk_condition,
        )
        langgraph.add_conditional_edges(
            "neighbor_exploration",
            gr.neighbor_condition,
        )
        langgraph.add_edge("answer_generation", END)

        self.graph_chain = langgraph.compile()  
  
        
    def __build_graph_reader(self, agent_config, phases_config, params):
        """
        Setup and return a GraphReader instance.
        """
        
        gr = GraphReader_base(agent_config, phases_config, params)
        gr.add_phase('rational_plan_creation_base', self.rational_plan_creation_base)
        gr.add_phase('extraction_question', self.extraction_question)
        gr.add_phase('initial_node_selection', self.initial_node_selection)
        gr.add_phase('atomic_fact_exploration', self.atomic_fact_exploration)
        gr.add_phase('chunk_exploration', self.chunk_exploration)
        gr.add_phase('all_chunks_exploration', self.all_chunks_exploration)
        gr.add_phase('question_generation', self.question_generation)
        gr.add_phase('neighbor_exploration', self.neighbor_exploration)
        gr.add_phase('answer_generation', self.answer_generation)
        
        return gr
    
    def get_answer(self, question:str, recursion_limit:int=50):
        start_time = datetime.datetime.now()
        result = self.graph_chain.invoke({"question": question}, {'recursion_limit' : recursion_limit})
        end_time = datetime.datetime.now()

        return result
    
    
    # response = graph_reader_base.get_answer(
    #     question="Dammi la definizione di provider",
    # )
    # print(response)
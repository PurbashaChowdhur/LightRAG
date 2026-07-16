import logging
import json
import argparse
import datetime
import os
import pickle
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings.global_variables import *
from settings.prompts import *
from src.utils._io import *
from src.utils.general_utils import *
from src.datamodule.gr_base import *
from src.datamodule.act import *
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END

def main(args):
    # Setup
    logging.basicConfig(level=logging.INFO)

    with open(f"{args.questions_dir}/with_ground_truth.json") as f:
        with_ground_truth = json.load(f)

    with open(f"{args.questions_dir}/without_ground_truth.json") as f:
        without_ground_truth = json.load(f)

    db = Neo4jGraph(
        url = NEO4J_URI,#args.neo4j_uri, 
        username = NEO4J_USERNAME,#args.neo4j_username, 
        password = NEO4J_PASSWORD#args.neo4j_password
    )

    embedding_openai = OpenAIEmbeddings(
        model = EMBEDDING_OPENAI,
        api_key = OPENAI_API_KEY,
        dimensions = EMBEDDING_DIMENSION
    )

    gpt = ChatOpenAI(
        model = MODEL,
        api_key = OPENAI_API_KEY
    )

    # Phases
    rational_plan_creation_base = Phase("rational_plan_creation_base",
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

    extraction_question = Phase("extraction_question",
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

    initial_node_selection = Phase("initial_node_selection",
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
    
    atomic_fact_exploration = Phase("atomic_fact_exploration",
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
    
    chunk_exploration = Phase("chunk_exploration",
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
    
    all_chunks_exploration = Phase("all_chunks_exploration",
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
    
    question_generation = Phase("question_generation",
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
    
    neighbor_exploration = Phase("neighbor_exploration",
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
    
    answer_generation = Phase("answer_generation",
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
        'embedding_model': embedding_openai,
        'embedding_model_name' : 'GPT'
    }

    params = {
        'k_potential_nodes' : 50,
        'k_initial_nodes' : 15,
        'max_chunks' : 20,
    }

    # Execution
    def build_graph_reader(agent_config, phases_config, params):
        """
        Setup and return a GraphReader instance.
        """
        
        gr = GraphReader_base(agent_config, phases_config, params)
        gr.add_phase('rational_plan_creation_base', rational_plan_creation_base)
        gr.add_phase('extraction_question', extraction_question)
        gr.add_phase('initial_node_selection', initial_node_selection)
        gr.add_phase('atomic_fact_exploration', atomic_fact_exploration)
        gr.add_phase('chunk_exploration', chunk_exploration)
        gr.add_phase('all_chunks_exploration', all_chunks_exploration)
        gr.add_phase('question_generation', question_generation)
        gr.add_phase('neighbor_exploration', neighbor_exploration)
        gr.add_phase('answer_generation', answer_generation)
        
        return gr

    # -- Questions without ground truth --
    def run_process_without(agent_config, params, question, key):    
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        configurations = {
            'chunk_exploration' : ['base', 'all_chunks']
        }

        for ce_config in configurations['chunk_exploration']:
            print(f"Running {ce_config} configuration for {key}...")

            sub_dirs = [f"CE {ce_config}"]

            log_file, _ = create_directories(
                'logs/without ground truth/GR base/', sub_dirs, key + '_' + timestamp
            )

            logger = setup_logger(log_file, f"GPT_RP base_INS question_CE {ce_config}")

            agent_config['logger'] = logger
            agent_config['embedding_model'] = embedding_openai
            agent_config['embedding_name'] = 'GPT'

            phases_config = {
                'rational_plan_creation': 'base',
                'initial_node_selection': 'question',
                'chunk_exploration': ce_config
            }

            gr = build_graph_reader(agent_config, phases_config, params)
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

            langgraph = langgraph.compile()
            
            start_time = datetime.datetime.now()
            result = langgraph.invoke({"question": question}, {'recursion_limit' : 50})
            end_time = datetime.datetime.now()
            
            print(f'Predicted references: {result["references"]}')
                    
            time_difference = end_time - start_time
            print(f"Time taken (s): {time_difference}")
            result['time'] = time_difference.total_seconds()
            print()
            
            pickle_dir = os.path.join(f'output/GR base/without ground truth/CE {ce_config}/')
            os.makedirs(pickle_dir, exist_ok=True)
            pickle_file = os.path.join(pickle_dir, f'{key}.pkl')
            with open(pickle_file, 'wb') as pf:
                pickle.dump(result, pf)
    
    for idx,(key,item) in enumerate(without_ground_truth.items()):
        if idx == 1:
            break
        print(f"Question: {item.get('question', 'No question provided')}")        
        run_process_without(agent_config, params, item.get('question'), key)

    # -- Questions with ground truth --
    def run_process_with(agent_config, params, question, key):    
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        configurations = {
            'chunk_exploration' : ['base', 'all_chunks']
        }

        for ce_config in configurations['chunk_exploration']:
            print(f"Running {ce_config} configuration for {key}...")

            sub_dirs = [f"CE {ce_config}"]

            log_file, _ = create_directories(
                'logs/with ground truth/GR base/', sub_dirs, key + '_' + timestamp
            )

            logger = setup_logger(log_file, f"GPT_RP base_INS question_CE {ce_config}")

            agent_config['logger'] = logger
            agent_config['embedding_model'] = embedding_openai
            agent_config['embedding_name'] = 'GPT'

            phases_config = {
                'rational_plan_creation': 'base',
                'initial_node_selection': 'question',
                'chunk_exploration': ce_config
            }

            gr = build_graph_reader(agent_config, phases_config, params)
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

            langgraph = langgraph.compile()
            
            start_time = datetime.datetime.now()
            result = langgraph.invoke({"question": question}, {'recursion_limit' : 50})
            end_time = datetime.datetime.now()
            
            print(f'Predicted references: {result["references"]}')
                    
            time_difference = end_time - start_time
            print(f"Time taken (s): {time_difference}")
            result['time'] = time_difference.total_seconds()
            print()
            
            pickle_dir = os.path.join(f'output/GR base/with ground truth/CE {ce_config}/')
            os.makedirs(pickle_dir, exist_ok=True)
            pickle_file = os.path.join(pickle_dir, f'{key}.pkl')
            with open(pickle_file, 'wb') as pf:
                pickle.dump(result, pf)

    for idx,(key,item) in enumerate(with_ground_truth.items()):
        if idx == 1:
            break
        print(f"Question: {item.get('question', 'No question provided')}")
        run_process_with(agent_config, params, item.get('question'), key)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--questions_dir', type=str, default="data/questions")
    parser.add_argument('--output_dir', type=str, default="output/graph_reader/base")
    parser.add_argument('--neo4j_uri', type=str, default=NEO4J_URI)
    parser.add_argument('--neo4j_username', type=str, default=NEO4J_USERNAME)
    parser.add_argument('--neo4j_password', type=str, default=NEO4J_PASSWORD)

    args = parser.parse_args()
    main(args)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model.state import *
from model.output import *
from utils.graph_reader.initial_node_selection import *
from utils.graph_reader.atomic_fact_exploration import *
from utils.graph_reader.chunk_exploration import *
from typing import Literal

class Phase():
    def __init__(self, name, gpt, prompt, output_parser = None):
        self.name = name
        self.gpt = gpt
        self.prompt = prompt
        if output_parser is not None:
            self.chain = prompt | gpt | output_parser
        else:
            self.chain = prompt | gpt

class GraphReader_base():
    def __init__(self, agent_config, phases_config, params):
        self.agent_config = agent_config
        self.phases_config = phases_config
        self.params = params
        self.phases = {}

    def add_phase(self, phase_name, phase):
        self.phases[phase_name] = phase

    def rational_plan_creation(self, state: InputState) -> OverallState:
        """
        Creates the rational plan based on the input question.

        Args:
        - state: The input state containing the user's question.

        Returns:
        - An OverallState object with the updated rational plan.
        """

        self.agent_config['logger'].info("\n")
        self.agent_config['logger'].info("RATIONAL PLAN CREATION")

        chain_rational_plan = self.phases["rational_plan_creation_base"].chain
        rational_plan = chain_rational_plan.invoke({"question": state['question']})

        self.agent_config['logger'].info(f"Rational plan: {rational_plan}")

        return OverallState(question=                state['question'],
                            rational_plan=           rational_plan,
                            notebook=                "",
                            previous_actions=        ["rational_plan_creation"],
                            check_atomic_facts_queue=[],
                            check_chunks_queue=      [],
                            neighbor_check_queue=    [],
                            chosen_action=           "",
                            selected_key_elements=    [],
                            selected_atomic_facts=    [],
                            visited_chunks=          [],
                            relevant_atomic_facts=   [],
                            relevant_chunks=         []
                            )
    
    def initial_node_selection(self, state: OverallState) -> OverallState:
        """
        Selects k initial KeyElement nodes based on the input question and rational plan.

        Args:
        - state: The current overall state.

        Returns:
        - An updated OverallState object with the selected initial KeyElement nodes.
        """
        
        self.agent_config['logger'].info("\n")
        self.agent_config['logger'].info("INITIAL KEY ELEMENT NODE SELECTION")
        
        match self.phases_config['initial_node_selection']:
            case "base":
                potential_nodes = retrieve_potential_nodes(self.agent_config['db'], 
                                                            self.agent_config['embedding_model'].embed_query(state['question']), 
                                                            self.params['k_potential_nodes'],
                                                            self.agent_config['embedding_name'])
                        
                self.agent_config['logger'].info(f"Potential nodes selected by the VectorIndex ({self.params['k_potential_nodes']}): {potential_nodes}")
                                            
                chain_initial_node = self.phases["initial_node_selection"].chain
                initial_nodes = chain_initial_node.invoke(
                    {
                        "question":      state['question'],
                        "rational_plan": state['rational_plan'],
                        "nodes":         potential_nodes,
                    }
                )
                
                check_atomic_facts_queue = [
                    el.key_element
                    for el in sorted(
                        initial_nodes.key_element_nodes,
                        key=lambda node: node.score,
                        reverse=True,
                    )
                ][:self.params['k_initial_nodes']]
            
            case "question":
                check_atomic_facts_queue = []

                chain_extraction_question = self.phases["extraction_question"].chain
                key_elements_question = retrieve_key_elements_question(chain_extraction_question, 
                                                                               state['question'])
                
                self.agent_config['logger'].info(f"KeyElements in the question: {key_elements_question}")

                for elem in key_elements_question:
                    data = self.agent_config['db'].query("""
                                        MATCH (k:KeyElement)
                                        WHERE k.content = $elem
                                        RETURN k.content AS content
                                        """,
                                        params={"elem": elem})

                    if data != []:
                        self.agent_config['logger'].info(f"KeyElement node for {elem} found with exact match.")    
                        check_atomic_facts_queue.append(data[0]['content'])
                    else:
                        self.agent_config['logger'].info(f"No KeyElement node for {elem} found with exact match. Searching for similar nodes.")
                        result = self.agent_config['db'].query(f"""
                                                MATCH (k:KeyElement)
                                                WHERE gds.similarity.cosine(k.embedding_{self.agent_config['embedding_name']}, {self.agent_config['embedding_model'].embed_query(elem)}) > 0.5
                                                WITH k, gds.similarity.cosine(k.embedding_{self.agent_config['embedding_name']}, {self.agent_config['embedding_model'].embed_query(elem)}) AS similarity
                                                RETURN k.content AS content
                                                ORDER BY similarity DESC
                                                """,
                                                params={"key_element": elem})
                        
                        if result == []:
                            self.agent_config['logger'].info(f"No similar node found for {elem}")
                        else:
                            self.agent_config['logger'].info(f"Most similar node found: {result[0]['content']}")
                            check_atomic_facts_queue.append(result[0]['content'])

            case _:
                raise ValueError("Invalid initial node selection mode.")
            
        if check_atomic_facts_queue == []:
            self.agent_config['logger'].info("No initial nodes found")
        else:
            self.agent_config['logger'].info(f"Initial KeyElement nodes ({self.params['k_initial_nodes']}): {check_atomic_facts_queue}")
        
        return OverallState(
            question=                 state['question'],
            rational_plan=            state['rational_plan'],
            notebook=                 state['notebook'],
            previous_actions=         ["initial_node_selection"],
            check_atomic_facts_queue= check_atomic_facts_queue,
            check_chunks_queue=       state['check_chunks_queue'],
            neighbor_check_queue=     state['neighbor_check_queue'],
            chosen_action=            "termination" if check_atomic_facts_queue == [] else state['chosen_action'],
            selected_key_elements=    check_atomic_facts_queue,
            selected_atomic_facts=    state['selected_atomic_facts'],
            visited_chunks=           state['visited_chunks'],
            relevant_atomic_facts=    state['relevant_atomic_facts'],
            relevant_chunks=          state['relevant_chunks']
        )

    def atomic_fact_exploration(self, state: OverallState) -> OverallState:
        """
        Explores the AtomicFact nodes from the queue, and updates the notebook.

        Args:
        - state: The current overall state.

        Returns:
        - An updated OverallState object after exploring the AtomicFact.
        """

        self.agent_config['logger'].info("\n")
        self.agent_config['logger'].info("ATOMIC FACT EXPLORATION")

        embedding_question = self.agent_config['embedding_model'].embed_query(state['question'])
        
        atomic_facts = get_atomic_facts_embedding_question(self.agent_config['db'], 
                                                            embedding_question,  
                                                            state['check_atomic_facts_queue'],
                                                            self.agent_config['embedding_name'],
                                                            0.6)
        
        if atomic_facts == []:
            self.agent_config['logger'].info("No AtomicFacts found with threshold 0.6. Retrying with threshold 0.4")
            atomic_facts = get_atomic_facts_embedding_question(self.agent_config['db'],
                                                               embedding_question,
                                                               state['check_atomic_facts_queue'],
                                                               self.agent_config['embedding_name'],
                                                               0.4)
            if atomic_facts == []:
                self.agent_config['logger'].info("No AtomicFacts found with threshold 0.4. Retrieving all AtomicFacts.")
                atomic_facts = get_atomic_facts_all(self.agent_config['db'],
                                                    state['check_atomic_facts_queue'])
        
        self.agent_config['logger'].info(f"Retrieved AtomicFacts: {len(atomic_facts)}")
        
        chain_atomic_fact_exploration = self.phases["atomic_fact_exploration"].chain
        atomic_facts_results = chain_atomic_fact_exploration.invoke(
            {
                "question":         state['question'],
                "rational_plan":    state['rational_plan'],
                "notebook":         state['notebook'],
                "atomic_facts":     atomic_facts
            }
        )

        notebook = atomic_facts_results.updated_notebook

        self.agent_config['logger'].info(f"Current notebook: {notebook}")
        self.agent_config['logger'].info(f"Relevant AtomicFacts: {atomic_facts_results.relevant_atomic_facts}")
        self.agent_config['logger'].info(f"Rational for next action after reading atomic facts: {atomic_facts_results.rational_next_action}")

        chosen_action = parse_function(atomic_facts_results.chosen_action)
        
        self.agent_config['logger'].info(f"Chosen action: {chosen_action}")

        response = OverallState(
            question=                 state['question'],
            rational_plan=            state['rational_plan'],
            notebook=                 notebook,
            previous_actions=         [f"atomic_fact_check({state['check_atomic_facts_queue']})"],
            check_atomic_facts_queue= [],
            check_chunks_queue=       state['check_chunks_queue'],
            neighbor_check_queue=     state['neighbor_check_queue'],
            chosen_action=            chosen_action.get("function_name"),
            selected_key_elements=    state['selected_key_elements'],
            selected_atomic_facts=    list(set(state['selected_atomic_facts'] + [af['atomic_fact_id'] for af in atomic_facts])),
            visited_chunks=           state['visited_chunks'],
            relevant_atomic_facts=    list(set(state['relevant_atomic_facts'] + atomic_facts_results.relevant_atomic_facts)),
            relevant_chunks=          state['relevant_chunks']
        )

        if chosen_action['function_name'] == "stop_and_read_neighbor":
            neighbors = get_neighbors_by_key_element(self.agent_config['db'], 
                                                     state['check_atomic_facts_queue'])
            
            response["neighbor_check_queue"] = neighbors

        elif chosen_action['function_name'] == "read_chunk":
            response["check_chunks_queue"] = chosen_action.get("arguments")[0]
            response["check_chunks_queue"] += retrieve_related_recitals(self.agent_config['db'],
                                                                        self.agent_config['embedding_model'].embed_query(state['question']),
                                                                       5,
                                                                       self.agent_config['embedding_name'])

        return response
    
    def chunk_exploration(self, state: OverallState) -> OverallState:
        """
        Explores the Chunks from the queue determined bu the previous step, and updates the notebook.

        Args:
        - state: The current OverallState.

        Returns:
        - An updated OverallState object after exploring the Chunks.
        """

        self.agent_config['logger'].info("\n")
        self.agent_config['logger'].info("CHUNK EXPLORATION")

        check_chunks_queue = state['check_chunks_queue']
        self.agent_config['logger'].info(f"Current Chunk queue: {check_chunks_queue}")  

        if check_chunks_queue != []:
            chunk_id = check_chunks_queue.pop(0)
            self.agent_config['logger'].info(f"Reading Chunk: {chunk_id}")
        else:
            self.agent_config['logger'].info("No more chunks to read.")
            return OverallState(
                question=                 state['question'],
                rational_plan=            state['rational_plan'],
                notebook=                 state['notebook'],
                previous_actions=         state['previous_actions'],
                check_atomic_facts_queue= state['check_atomic_facts_queue'],
                check_chunks_queue=       state['check_chunks_queue'],
                neighbor_check_queue=     state['neighbor_check_queue'],
                chosen_action=            "termination",
                selected_key_elements=    state['selected_key_elements'],
                selected_atomic_facts=    state['selected_atomic_facts'],
                visited_chunks=           state['visited_chunks'],
                relevant_atomic_facts=    state['relevant_atomic_facts'],
                relevant_chunks=          state['relevant_chunks']
            )

        if state['visited_chunks'] == []:
            state["visited_chunks"] = [chunk_id]
        else:
            if chunk_id in state["visited_chunks"]:
                self.agent_config['logger'].info(f"Chunk {chunk_id} has already been visited.")
                return OverallState(
                    question=                 state['question'],
                    rational_plan=            state['rational_plan'],
                    notebook=                 state['notebook'],
                    previous_actions=         state['previous_actions'],
                    check_atomic_facts_queue= state['check_atomic_facts_queue'],
                    check_chunks_queue=       state['check_chunks_queue'],
                    neighbor_check_queue=     state['neighbor_check_queue'],
                    chosen_action=            "search_more",
                    selected_key_elements=    state['selected_key_elements'],
                    selected_atomic_facts=    state['selected_atomic_facts'],
                    visited_chunks=           state['visited_chunks'],
                    relevant_atomic_facts=    state['relevant_atomic_facts'],
                    relevant_chunks=          state['relevant_chunks']
                )
            else:
                state["visited_chunks"].append(chunk_id)

                if len(state['visited_chunks']) == self.params['max_chunks']:
                    self.agent_config['logger'].info(f"Visited the max number of chunks: {self.params['max_chunks']} chunks.")
                    return OverallState(
                        question=                 state['question'],
                        rational_plan=            state['rational_plan'],
                        notebook=                 state['notebook'],
                        previous_actions=         state['previous_actions'],
                        check_atomic_facts_queue= state['check_atomic_facts_queue'],
                        check_chunks_queue=       state['check_chunks_queue'],
                        neighbor_check_queue=     state['neighbor_check_queue'],
                        chosen_action=            "termination",
                        selected_key_elements=    state['selected_key_elements'],
                        selected_atomic_facts=    state['selected_atomic_facts'],
                        visited_chunks=           state['visited_chunks'],
                        relevant_atomic_facts=    state['relevant_atomic_facts'],
                        relevant_chunks=          state['relevant_chunks']
                    ) 
                 
        reference_annex = get_reference_chunks_annex(self.agent_config['db'], chunk_id)

        if reference_annex == []:
            self.agent_config['logger'].info("No reference to annnexes found.")
        else:
            check_chunks_queue = list(set(reference_annex + check_chunks_queue))
            self.agent_config['logger'].info(f"Found reference for annex: {reference_annex}")

        related_recitals = get_related_recitals_chunk(self.agent_config['db'], chunk_id)

        if related_recitals == []:
            self.agent_config['logger'].info("No related recitals for this chunk, retrieving related recitals from the article.")
            article_id = get_article_by_chunk_id(chunk_id)
            related_recitals = get_related_recitals_article(self.agent_config['db'], article_id)

            if related_recitals == []:
                self.agent_config['logger'].info("No related recitals for this article.")
            else:
                self.agent_config['logger'].info(f"Related recital(s): {related_recitals}")
        else:
            self.agent_config['logger'].info(f"Related recital(s): {related_recitals}")

        check_chunks_queue = list(set(related_recitals + check_chunks_queue))

        chunks_text = get_chunk(self.agent_config['db'], chunk_id)

        match self.phases_config['chunk_exploration']:
            case 'base':
                chain_chunk_exploration = self.phases["chunk_exploration"].chain
                read_chunk_results = chain_chunk_exploration.invoke(
                    {
                        "question":         state['question'],
                        "rational_plan":    state['rational_plan'],
                        "previous_actions": state['previous_actions'],
                        "notebook":         state['notebook'],
                        "chunk":            chunks_text
                    }
                )
                notebook = read_chunk_results.updated_notebook
                
                self.agent_config['logger'].info(f"Current notebook: {notebook}")
                self.agent_config['logger'].info(f"Rational for next action after reading chunk: {read_chunk_results.rational_next_move}")
                
                chosen_action = parse_function(read_chunk_results.chosen_action)
                self.agent_config['logger'].info(f"Chosen action: {chosen_action}")

                if read_chunk_results.relevant_chunk:
                    self.agent_config['logger'].info(f"Chunk {chunk_id} is relevant to the question.")
                else:
                    self.agent_config['logger'].info(f"Chunk {chunk_id} is not relevant to the question.")

                self.agent_config['logger'].info(f"Relevant chunks: {state['relevant_chunks']}")

                if read_chunk_results.relevant_chunk:
                    if state['relevant_chunks'] == []:
                        state["relevant_chunks"] = [chunk_id]
                    else:
                        state["relevant_chunks"].append(chunk_id)

                response = OverallState(
                    question=                 state['question'],
                    rational_plan=            state['rational_plan'],
                    notebook=                 notebook,
                    previous_actions=         [f"read_chunk({chunk_id})"],
                    check_atomic_facts_queue= state['check_atomic_facts_queue'],
                    check_chunks_queue=       check_chunks_queue,
                    neighbor_check_queue=     state['neighbor_check_queue'],
                    chosen_action=            chosen_action.get("function_name"),
                    selected_key_elements=    state['selected_key_elements'],
                    selected_atomic_facts=    state['selected_atomic_facts'],
                    visited_chunks=           state['visited_chunks'],
                    relevant_atomic_facts=    state['relevant_atomic_facts'],
                    relevant_chunks=          state['relevant_chunks']
                )

                if chosen_action.get("function_name") == "read_subsequent_chunk":
                    subsequent_id = get_subsequent_chunk_id(self.agent_config['db'], chunk_id)
                    if subsequent_id != []:
                        check_chunks_queue.append(subsequent_id[0]['next'])
                    else:
                        if check_chunks_queue == []:
                            response["chosen_action"] = "termination"

                elif chosen_action.get("function_name") == "read_previous_chunk":
                    previous_id = get_previous_chunk_id(self.agent_config['db'], chunk_id)
                    if previous_id != []:   
                        check_chunks_queue.append(previous_id[0]['previous'])
                    
                elif chosen_action.get("function_name") == "search_more":
                    if check_chunks_queue == []:
                        response["chosen_action"] = "search_neighbor"    
                        chain_question_generation = self.phases["question_generation"].chain
                        generated_question = chain_question_generation.invoke(
                            {
                                "question": state['question'],
                                "rational_plan": state['rational_plan'],
                                "notebook": state['notebook'],
                            }
                        )

                        self.agent_config['logger'].info(f"Generated question from rational_plan: {generated_question.generated_question}")
                        
                        neighbors = retrieve_potential_nodes(self.agent_config['db'], 
                                                             self.agent_config['embedding_model'].embed_query(generated_question.generated_question),
                                                             self.params['k_potential_nodes'],
                                                             self.agent_config['embedding_name'])
                        
                        neighbors = [n for n in neighbors if n not in response["selected_key_elements"]]

                        if neighbors == []:
                            self.agent_config['logger'].info("No more neighbors to explore.")
                            response["chosen_action"] = "termination"
                        else: 
                            self.agent_config['logger'].info(f"Potential (filtered) neighbors: {neighbors}")

                            response["selected_key_elements"] = response["selected_key_elements"] + neighbors
                            response["neighbor_check_queue"] = neighbors
                            response["question"] = generated_question.generated_question

                response["check_chunks_queue"] = check_chunks_queue
                return response
            
            case 'all_chunks':
                chain_chunk_exploration = self.phases["all_chunks_exploration"].chain
                read_chunk_results = chain_chunk_exploration.invoke(
                    {
                        "question":         state['question'],
                        "rational_plan":    state['rational_plan'],
                        "previous_actions": state['previous_actions'],
                        "notebook":         state['notebook'],
                        "chunk":            chunks_text
                    }
                )

                notebook = read_chunk_results.updated_notebook
                
                self.agent_config['logger'].info(f"Current notebook: {notebook}")
                self.agent_config['logger'].info(f"Do we need to search for more information?: {read_chunk_results.search_more}")
                
                if read_chunk_results.relevant_chunk:
                    self.agent_config['logger'].info(f"Chunk {chunk_id} is relevant to the question.")
                else:
                    self.agent_config['logger'].info(f"Chunk {chunk_id} is not relevant to the question.")

                self.agent_config['logger'].info(f"Relevant chunks: {state['relevant_chunks']}")

                if read_chunk_results.relevant_chunk:
                    if state['relevant_chunks'] == []:
                        state["relevant_chunks"] = [chunk_id]
                    else:
                        state["relevant_chunks"].append(chunk_id)

                response = OverallState(
                    question=                 state['question'],
                    rational_plan=            state['rational_plan'],
                    notebook=                 notebook,
                    previous_actions=         [f"read_chunk({chunk_id})"],
                    check_atomic_facts_queue= state['check_atomic_facts_queue'],
                    check_chunks_queue=       check_chunks_queue,
                    neighbor_check_queue=     state['neighbor_check_queue'],
                    chosen_action=            "search_more", 
                    selected_key_elements=     state['selected_key_elements'],
                    selected_atomic_facts=     state['selected_atomic_facts'],
                    visited_chunks=           state['visited_chunks'],
                    relevant_atomic_facts=    state['relevant_atomic_facts'],
                    relevant_chunks=          state['relevant_chunks']
                )

                if read_chunk_results.search_more:
                    if check_chunks_queue == []:
                        response["chosen_action"] = "search_neighbor"    
                        chain_question_generation = self.phases["question_generation"].chain
                        
                        generated_question = chain_question_generation.invoke(
                            {
                                "question": state['question'],
                                "rational_plan": state['rational_plan'],
                                "notebook": state['notebook'],
                            }
                        )

                        self.agent_config['logger'].info(f"Generated question from rational_plan: {generated_question.generated_question}")
                        
                        neighbors = retrieve_potential_nodes(self.agent_config['db'], 
                                                             self.agent_config['embedding_model'].embed_query(generated_question.generated_question),
                                                             self.params['k_potential_nodes'],
                                                             self.agent_config['embedding_name'])
                        
                        neighbors = [n for n in neighbors if n not in response["selected_key_elements"]]

                        if neighbors == []:
                            self.agent_config['logger'].info("No more neighbors to explore.")
                            response["chosen_action"] = "termination"
                        else: 
                            self.agent_config['logger'].info(f"Potential (filtered) neighbors: {neighbors}")

                            response["selected_key_elements"] = response["selected_key_elements"] + neighbors
                            response["neighbor_check_queue"] = neighbors
                            response["question"] = generated_question.generated_question

                response["check_chunks_queue"] = check_chunks_queue
                return response

    def neighbor_exploration(self, state: OverallState) -> OverallState:
        """
        Explores the neighbors from the queue, and updates the notebook.

        Args:
        - state: The current overall state.

        Returns:
        - An updated OverallState object after selecting the neighbors.
        """

        self.agent_config['logger'].info("\n")
        self.agent_config['logger'].info("NEIGHBOR EXPLORATION")
        self.agent_config['logger'].info(f"Exploring the following neighbor nodes: {state['neighbor_check_queue']}")

        chain_neighbor_exploration = self.phases["neighbor_exploration"].chain
        neighbor_select_results = chain_neighbor_exploration.invoke(
            {
                "question":         state['question'],
                "rational_plan":    state['rational_plan'],
                "notebook":         state['notebook'],
                "nodes":            state['neighbor_check_queue'],
            }
        )

        self.agent_config['logger'].info(f"Rational for next action after reading neighbors: {neighbor_select_results.rational_next_move}")

        chosen_action = parse_function(neighbor_select_results.chosen_action)
        
        self.agent_config['logger'].info(f"Chosen action: {chosen_action}")
        
        response = OverallState(
            question=                 state['question'],
            rational_plan=            state['rational_plan'],
            notebook=                 state['notebook'],
            previous_actions=         [f"neighbor_select({chosen_action.get('arguments', [''])[0] if chosen_action.get('arguments', ['']) else ''})"],
            check_atomic_facts_queue= state['check_atomic_facts_queue'],
            check_chunks_queue=       state['check_chunks_queue'],
            neighbor_check_queue=     [],
            chosen_action=            chosen_action['function_name'],
            selected_key_elements=     state['selected_key_elements'],
            selected_atomic_facts=     state['selected_atomic_facts'],
            visited_chunks=           state['visited_chunks'],
            relevant_atomic_facts=    state['relevant_atomic_facts'],
            relevant_chunks=          state['relevant_chunks']
        )

        if chosen_action['function_name'] == "read_neighbor_node":
            response["check_atomic_facts_queue"] = [chosen_action.get("arguments")[0]]
        return response

    def answer_generation(self, state: OverallState) -> OutputState:
        """
        Answers the question based on the content of the notebook.

        Args:
        - state: The current overall state.

        Returns:
        - An OutputState object with the final answer, analysis and previous actions.
        """

        self.agent_config['logger'].info("\n")
        self.agent_config['logger'].info("ANSWER GENERATION")
        self.agent_config['logger'].info(f"Answering the question: {state['question']}")

        chain_answer_generation = self.phases["answer_generation"].chain
        final_answer = chain_answer_generation.invoke(
            {
                "question": state['question'], 
                "notebook": state['notebook']
            }
        )

        self.agent_config['logger'].info(f"Predicted Answer: {final_answer.final_answer}")
        
        references = {
            "articles": [get_article_by_chunk_id(chunk) for chunk in state['relevant_chunks'] if not chunk.startswith('Recital')],
            "recitals": [get_article_by_chunk_id(chunk) for chunk in state['relevant_chunks'] if chunk.startswith('Recital')]
        }

        self.agent_config['logger'].info(f"Predicted References: {references}")

        return OutputState(answer=                  final_answer.final_answer,
                            previous_actions=       ["answer_generation"],
                            selected_key_elements=  state['selected_key_elements'],
                            selected_atomic_facts=  state['selected_atomic_facts'],
                            visited_chunks =        state['visited_chunks'],
                            references=             references
                            )

    @staticmethod
    def atomic_fact_condition(state: OverallState) -> Literal["neighbor_exploration", "chunk_exploration"]:
        if state['chosen_action'] == "stop_and_read_neighbor":
            return "neighbor_exploration"
        
        elif state['chosen_action'] == "read_chunk":
            return "chunk_exploration"

    @staticmethod
    def chunk_condition(state: OverallState,) -> Literal["answer_generation", "chunk_exploration", "neighbor_exploration"]:
        if state['chosen_action'] == "termination":
            return "answer_generation"
        
        elif state['chosen_action'] in ["read_subsequent_chunk", "read_previous_chunk", "search_more"]:
            return "chunk_exploration"
        
        elif state['chosen_action'] == "search_neighbor":
            return "neighbor_exploration"

    @staticmethod
    def neighbor_condition(state: OverallState,) -> Literal["answer_generation", "atomic_fact_exploration"]:
        if state['chosen_action'] == "termination":
            return "answer_generation"
        
        elif state['chosen_action'] == "read_neighbor_node":
            return "atomic_fact_exploration"
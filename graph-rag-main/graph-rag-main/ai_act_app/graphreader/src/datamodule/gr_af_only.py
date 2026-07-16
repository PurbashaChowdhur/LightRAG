from .gr_base import *

class GraphReader_af_only(GraphReader_base):
    def __init__(self, agent_config, phases_config, params):
        super().__init__(agent_config, phases_config, params)

    def add_phase(self, phase_name, phase):
        return super().add_phase(phase_name, phase)

    def rational_plan_creation(self, state):
        return super().rational_plan_creation(state)
    
    def atomic_fact_exploration(self, state):
        self.agent_config['logger'].info("\n")
        self.agent_config['logger'].info("ATOMIC FACT EXPLORATION")

        atomic_facts = get_atomic_facts_vector_index(self.agent_config['db'], 
                                                                    self.params['k_atomic_facts'], 
                                                                    self.agent_config['embedding_model'].embed_query(state['question']),
                                                                    self.agent_config['embedding_name'])
                        
        self.agent_config['logger'].info(f"Number of retrieved Atomic facts: {len(atomic_facts)}")

        chain_atomic_fact_exploration = self.phases["atomic_fact_exploration"].chain
        atomic_facts_results = chain_atomic_fact_exploration.invoke(
            {
                "question":         state['question'],
                "rational_plan":    state.get("rational_plan"),
                "notebook":         state.get("notebook"),
                "atomic_facts":     atomic_facts,
            }
        )

        notebook = atomic_facts_results.updated_notebook

        self.agent_config['logger'].info(f"Current notebook: {notebook}")
        self.agent_config['logger'].info(f"Relevant atomic facts: {atomic_facts_results.relevant_atomic_facts}")
        self.agent_config['logger'].info(f"Rational for next action after reading atomic facts: {atomic_facts_results.rational_next_action}")

        chosen_action = parse_function(atomic_facts_results.chosen_action)
        
        self.agent_config['logger'].info(f"Chosen action: {chosen_action}")

        response = OverallState(
            question=                 state['question'],
            rational_plan=            state.get("rational_plan"),
            notebook=                 notebook,
            previous_actions=         [f"atomic_fact_check({state.get('check_atomic_facts_queue')})"],
            check_atomic_facts_queue= [],
            check_chunks_queue=       state.get("check_chunks_queue"),
            neighbor_check_queue=     state.get("neighbor_check_queue"),
            chosen_action=            chosen_action.get("function_name"),
            selected_key_elements=     state.get("selected_key_elements"),
            selected_atomic_facts=     list(set(state['selected_atomic_facts'] + [af['atomic_fact_id'] for af in atomic_facts])),
            visited_chunks=           state.get("visited_chunks"),
            relevant_atomic_facts=    list(set(state['relevant_atomic_facts'] + atomic_facts_results.relevant_atomic_facts)),
            relevant_chunks=          state.get("relevant_chunks")            
        )

        if chosen_action['function_name'] == "stop_and_read_neighbor":
            neighbors = get_neighbors_by_key_element(self.agent_config['db'], state.get('check_atomic_facts_queue'))
            response["neighbor_check_queue"] = neighbors

        elif chosen_action['function_name'] == "read_chunk":
            response["check_chunks_queue"] = chosen_action.get("arguments")[0]
            response["check_chunks_queue"] += retrieve_related_recitals(self.agent_config['db'],
                                                                        self.agent_config['embedding_model'].embed_query(state['question']),
                                                                       5,
                                                                       self.agent_config['embedding_name'])

        return response

    def chunk_exploration(self, state):
        return super().chunk_exploration(state)
    
    def neighbor_exploration(self, state):
        return super().neighbor_exploration(state)
    
    def answer_generation(self, state):
        return super().answer_generation(state)
    
    @staticmethod
    def atomic_fact_condition(state: OverallState) -> Literal["neighbor_exploration", "chunk_exploration"]:
        if state.get("chosen_action") == "stop_and_read_neighbor":
            return "neighbor_exploration"
        
        elif state.get("chosen_action") == "read_chunk":
            return "chunk_exploration"
    
    @staticmethod
    def chunk_condition(state: OverallState,) -> Literal["answer_generation", "chunk_exploration", "neighbor_exploration"]:
        if state.get("chosen_action") == "termination":
            return "answer_generation"
        
        elif state.get("chosen_action") in ["read_subsequent_chunk", "read_previous_chunk", "search_more"]:
            return "chunk_exploration"
        
        elif state.get("chosen_action") == "search_neighbor":
            return "neighbor_exploration"
    
    @staticmethod
    def neighbor_condition(state: OverallState,) -> Literal["answer_generation", "atomic_fact_exploration"]:
        if state.get("chosen_action") == "termination":
            return "answer_generation"
        
        elif state.get("chosen_action") == "read_neighbor_node":
            return "atomic_fact_exploration"
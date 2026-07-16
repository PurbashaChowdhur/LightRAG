from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="hf.co/SciPhi/Triplex:Q4_K_M",
    temperature=0,
    format="",
    base_url="http://labs.larus-ba.it/ollama"
    # other params ...
)

messages = [
    # ("system", "You are a helpful translator. Translate the user sentence to French."),
    (
        "human",
        """Perform Named Entity Recognition (NER) and extract knowledge graph triplets from the text. NER identifies named entities of given entity types, and triple extraction identifies relationships between entities using specified predicates.

           **Entity Types:**
           ["LOCATION", "POSITION", "DATE", "CITY", "COUNTRY", "NUMBER"]

           **Predicates:**
           ["POPULATION", "AREA"]

           **Text:**
           San Francisco,[24] officially the City and County of San Francisco, is a commercial, financial, and cultural center in Northern California. 
            With a population of 808,437 residents as of 2022, San Francisco is the fourth most populous city in the U.S. state of California behind Los Angeles, San Diego, and San Jose.
        """
    ),
]

response = llm.invoke(
    messages
)
print(response)
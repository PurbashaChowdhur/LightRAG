import os
import streamlit as st
import streamlit_authenticator as stauth
import yaml
import json
import requests
import pymongo

from yaml.loader import SafeLoader
from urllib.parse import quote_plus
from bson import ObjectId
from model import RatedResponse


# Aggiungere la valutazione:
# Ricordare la domanda, la risposta e l'intero della valutazione
# Inserire un'altra API POST per salvare queste tre cose

# Credentials viene passato come dizionario json

light_rag_endpoint = os.environ.get("FAST_API_LIGHTRAG_ENDPOINT")
st.write(light_rag_endpoint)
graph_reader_endpoint = os.environ.get("FAST_API_GRAPHREADER_ENDPOINT")
st.write(graph_reader_endpoint)

placeholder = st.empty()
# placeholder.markdown("# Pagina di login")

st.logo(
    image="akos_ai_white_logo_on_indigo-removebg.png",
    link="https://www.akos-ai.com",
    size="large",
    icon_image="akos_ai_indigo_logo_with_name.jpeg",
)

def send_feedback(question, response, index):
    st.session_state.history[index]["feedback"] = st.session_state[f"feedback_{index}"]
    st.session_state.history[index]["expected_answer"] = st.session_state[f"expected_answer_{index}"]
    
    rated_response = RatedResponse(
        question=question,
        response=response,
        feedback=st.session_state.history[index]["feedback"] + 1,
        expected_answer=st.session_state.history[index]["expected_answer"],
    )
    try:
        requests.post(f"{light_rag_endpoint}/lightrag/ratedResponse", json=rated_response.model_dump(mode="json"))
    except requests.exceptions.RequestException as e:
        return None
    
@st.cache_resource(show_spinner=False)
def init_connection():
    uri = "mongodb://%s:%s@%s:%s" % (quote_plus(st.secrets["mongo"]["username"]), quote_plus(st.secrets["mongo"]["password"]), os.environ.get("MONGO_DB_HOSTNAME"), st.secrets["mongo"]["port"])
    print(uri)
    return pymongo.MongoClient(uri)

client = init_connection()

def fix_oid(doc):
    if "_id" in doc and isinstance(doc["_id"], dict) and "$oid" in doc["_id"]:
        doc["_id"] = ObjectId(doc["_id"]["$oid"])
    return doc

@st.cache_data(ttl=600, show_spinner=False)
def get_users():
    db = client['admin']
    collection = db['users']
    items = collection.find()
    #items = list(items)  # make hashable for st.cache_data
    if not items:
        with open('ai_act_users.json') as f:
            credential_file = json.load(f)
            fixed_credential = [fix_oid(d) for d in credential_file]
            collection.insert_many(fixed_credential)

    items = collection.find()
    items = list(items)
    data = {
        "credentials": {
            "usernames": {}
        }
    }

    for i in range(len(items)):
        username = items[i]["username"]
        if username:
           data["credentials"]["usernames"][username] = {
                "email": items[i]["email"],
                "name": items[i]["name"],
                "password": items[i]["password"]
           }
    return data

@st.cache_resource(show_spinner=False)
def config_loader():  # chunk_token_size,llm_model_max_token_size,chunk_overlap_token_size):
    config_data = {
        "chunk_token_size": 512,  # chunk_token_size,
        "llm_model_max_token_size": 32768,  # llm_model_max_token_size,
        "chunk_overlap_token_size": 256  # chunk_overlap_token_size
    }
    try:
        response = requests.post(f"{light_rag_endpoint}/lightrag/configuration", json=config_data)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Errore durante il caricamento della configurazione dei token: {e}")
        return None

@st.cache_resource(show_spinner=False)
def loader():
    try:
        response = requests.post(f"{light_rag_endpoint}/lightrag/load")
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        st.error(f"Errore durante il caricamento dei documenti: {e}")
        return None


with st.spinner(text="Caricamento...",show_time=True):
    users_json = json.dumps(get_users())
    credential = json.loads(users_json)

with open('authentication_settings.yaml',"r") as authentication_settings:
    authentication_settings = yaml.load(authentication_settings, Loader=SafeLoader)
    authenticator = stauth.Authenticate(
        credential['credentials'],
        authentication_settings['cookie']['name'],
        authentication_settings['cookie']['key'],
        authentication_settings['cookie']['expiry_days']
    )

authenticator.login(location='main', key='Login')

if st.session_state.get('authentication_status'):
    with placeholder.container():
        placeholder.text(f"""
            Benvenuto {st.session_state.get("name")}!! 
            Questo è un agente che risponde a domande relative al regolamento europeo sull'intelligenza artificiale (AI ACT). 
            Ti chiediamo di valutare le risposte e dare un rating da 1 a 5.
            La tua utenza è utilizzata ai soli fini di accesso all'applicazione. 
            Le domande, le relative risposte e il rating fornito sono memorizzati senza alcun riferimento all'utenza che ha fatto accesso all'applicazione.
        """)
    
    authenticator.logout(location="sidebar")
    
    model = st.sidebar.radio(label="Seleziona il modello da utilizzare:",
                options=["LightRAG", "GraphRAG"],
                index=0,
                key="type_model"
                )
    st.sidebar.write("""
        Qui puoi configurare in quale modo l'agente ricerca le informazioni per rispondere alle tue domande.
        L'agente può adottare le seguenti modalità:
        - local, ricerca locale che si basa solamente sulle informazioni dipendenti dal contesto
        - globale, ricerca globale che si basa sulla conoscenza globale
        - hybrid, ricerca ibrida che mette insieme informazioni locali contestuali e conoscenza globale
        - naive, ricerca semplificata senza combinare altre modalità avanzate
        - mix, ricerca che combina il meglio delle modalità RAG
    """)

    if model == 'LightRAG':
        model_option = st.sidebar.radio(
            "Seleziona la modalità di ricerca:",
            ["local", "global", "hybrid", "naive", "mix", "bypass"],
            index=4
        )

        # chunk_token_size =st.sidebar.number_input(label="chunk_token_size:",value=512,step=1)
        # llm_model_max_token_size = st.sidebar.number_input(label="llm_model_max_token_size:",value=32768,step=1)
        # chunk_overlap_token_size = st.sidebar.number_input(label="chunk_overlap_token_size:",value=256,step=1)

        # if (chunk_token_size and llm_model_max_token_size and chunk_overlap_token_size) is not (None or 0):
        # chunk_token_size,llm_model_max_token_size,chunk_overlap_token_size)

        #with st.spinner("Caricamento...", show_time=True):
        #    start = time.perf_counter()
    with st.spinner("Caricamento...", show_time=True):
        configuration = config_loader()
        num_docs = loader()
    tot_documenti = st.sidebar.write(f"Totale documenti: {num_docs['num_documents']}")

    if "history" not in st.session_state:
        st.session_state.history = []
        
        # history = list(dict) {"role": "user" or "assistant", "content": question of the user or answer of the model}
        # st.write("History:", st.session_state.history)

        # used for displaying the whole conversation
    for i, message in enumerate(st.session_state.history):
        with st.chat_message(message["role"]):
            st.write(message["content"])
            #st.write(message['feedback'])
            #st.write(message['expected_answer'])

            if message["role"] == "assistant":                
                feedback = message.get("feedback", None)
                
                st.session_state[f"feedback_{i}"] = feedback

                #st.write("Valutazione della risposta:")
                #st.write(f"Valutazione: {feedback}")
                
                st.feedback(
                    "stars",
                    key=f"feedback_{i}",
                    disabled=True,
                )
            
                expected_answer = message.get("expected_answer", None)
            
                st.session_state[f"expected_answer_{i}"] = expected_answer

                #st.write("Risposta attesa:")
                #st.write(f"Risposta attesa: {expected_answer}")
            
                st.text_area(
                    label="Inserisci la risposta che ti saresti aspettato se quella che ti ho fornito non è soddisfacente",
                    key=f"expected_answer_{i}",
                    disabled = True,
                )
                
    if question := st.chat_input("Scrivi qui la tua domanda..."):
        st.chat_message("user").markdown(question)

        if model == 'LightRAG':
            response = requests.get(f"{light_rag_endpoint}/lightrag/answer?question={question}&mode={model_option}")
        else:
            response = requests.get(f"{graph_reader_endpoint}/gr_base?question={question}")

        st.session_state.history.append({"role": "user", "content": question})
    
        chatbot_response: str = response.json()["response"]
        chatbot_response = chatbot_response.replace("./cached_articles", f"http://labs.larus-ba.it/app/static")

        with st.chat_message("assistant"):
            st.write(chatbot_response)
            index = len(st.session_state.history)-1

            with st.form(key="feedback_form", enter_to_submit=False):
                number_of_stars = st.feedback(
                    "stars",
                    key=f"feedback_{index}",
                    #args=[question, chatbot_response, index],
                ) 

                user_expected_answer = st.text_area(
                    label="Inserisci la risposta che ti saresti aspettato se quella che ti ho fornito non è soddisfacente",
                    key=f"expected_answer_{index}",
                    #args=[index]
                )

                st.form_submit_button(label="Invia feedback", on_click = send_feedback, args = [question, chatbot_response, index])
                
                #st.session_state[f"feedback_{index}"] = number_of_stars
                #st.session_state[f"expected_answer_{index}"] = user_expected_answer

                st.session_state.history.append({"role": "assistant", 
                                                "content": chatbot_response, 
                                                "expected_answer": user_expected_answer,
                                                "feedback": number_of_stars})


elif st.session_state.get('authentication_status') is False:
     st.error('Username o password non corretti')
elif st.session_state.get('authentication_status') is None:
     st.warning('Per favore inserisci il tuo username e la tua password')
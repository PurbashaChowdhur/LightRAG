import streamlit as st
import requests

# from rag import RAG

# @st.cache_resource
# def get_rag():
#     rag = RAG()
#
#     return rag

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": """
                Questo è un chatbot che risponde a domande sulla normativa NIS2
            """
        }
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    last_message_user = st.session_state.messages[-1]["content"]

    # response = get_rag().get_answer(question=last_message_user)
    resp = requests.get("http://localhost:8000/response?question=" + last_message_user)
    response: str = resp.json()["response"]
    response = response.replace("./cached_articles", f"http://labs.larus-ba.it/app/static")
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.chat_message("assistant").write(response)

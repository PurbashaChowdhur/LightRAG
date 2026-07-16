import streamlit as st
import requests
from ai_act.rag import RAG

def main():
    st.title("GraphRAG")

    model = st.selectbox("Select a model", ["LightRAG"])
    dataset = st.selectbox("Select a dataset", ["AI ACT", "NIS2"])
    question = st.text_input("Enter your question")
    submit_button = st.button("Submit")

    if submit_button:
        if model == "LightRAG":
            if dataset == "AI ACT":
                rag = RAG()
                url = "http://localhost:8000/ai_act"
            elif dataset == "NIS2":
                url = "http://localhost:8000/nis2"

            response = rag.execute(question=question)

        else:
            st.error("Model not supported yet.")
        
        st.text_area("Response", value="", height=300)
        st.text_area("Question", value=question, height=100)
        st.text_area("Answer", value=response.json(), height=100)
        st.text_area("Sources", value="", height=100)

if __name__ == "__main__":
    main()
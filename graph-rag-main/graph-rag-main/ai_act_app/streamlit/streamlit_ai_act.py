# Per far partire il codice è necessario su terminale scrivere questo: 
 
# streamlit run your_script.py
# OPPURE
# python -m streamlit run your_script.py

import streamlit as st

main_page = st.Page("main_page.py", title="Pagina principale")
pg = st.navigation([main_page])

pg.run()
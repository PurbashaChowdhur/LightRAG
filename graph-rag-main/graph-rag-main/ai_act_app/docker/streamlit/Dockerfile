FROM python:3.13.3-slim

WORKDIR /streamlit

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir .streamlit
COPY .streamlit/config.toml .streamlit
COPY .streamlit/secrets.toml .streamlit
COPY model.py .
COPY main_page.py .
COPY streamlit_ai_act.py .
COPY credentials.json .
#COPY data_transferer.py .
COPY ai_act_users.json .
COPY authentication_settings.yaml .
COPY requirements.txt .
COPY akos_ai_white_logo_on_indigo-removebg.png .
COPY akos_ai_indigo_logo_with_name.jpeg .

RUN pip3 install -r requirements.txt

EXPOSE 8502

HEALTHCHECK CMD curl --fail http://localhost:8502/_stcore/health

ENTRYPOINT ["streamlit", "run", "streamlit_ai_act.py", "--server.port=8502", "--server.address=0.0.0.0"]
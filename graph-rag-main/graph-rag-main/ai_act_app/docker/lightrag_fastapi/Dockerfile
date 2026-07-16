FROM python:3.13.3-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY app.py .
COPY rag.py .
COPY model.py .
COPY minio_executor.py .
#COPY data_transferer.py .

RUN mkdir rag
COPY rag/*.* ./rag

EXPOSE 8090

CMD ["fastapi", "run", "app.py", "--port", "8090"]
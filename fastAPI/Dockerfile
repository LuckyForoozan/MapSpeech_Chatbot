FROM python:3.12-slim
WORKDIR /app
COPY fastAPI/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fastAPI/main.py fastAPI/ui.py ./
CMD ["sh", "-c", "uvicorn main:app --host 127.0.0.1 --port 8000 & streamlit run ui.py --server.port=${PORT:-10000} --server.address=0.0.0.0"]

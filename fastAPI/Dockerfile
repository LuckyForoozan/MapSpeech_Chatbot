FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py ui.py location_tool.py ./
CMD ["sh", "-c", "uvicorn main:app --host 127.0.0.1 --port 8000 & streamlit run ui.py --server.port=${PORT:-10000} --server.address=0.0.0.0"]

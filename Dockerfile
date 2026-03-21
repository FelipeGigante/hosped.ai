FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the HuggingFace embedding model so Cloud Run doesn't hit rate limits at startup
# Must use HuggingFaceEmbeddings (same as runtime code) — it caches to ~/.cache/huggingface/hub/
# SentenceTransformer alone uses a different cache path and would NOT be found at runtime
RUN python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

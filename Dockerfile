FROM python:3.12-slim

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend /app/backend
COPY classifier /app/classifier
COPY eval /app/eval
COPY evaluation /app/evaluation
COPY fusion /app/fusion
COPY live /app/live
COPY policy /app/policy
COPY signals /app/signals
COPY storage /app/storage
RUN python -c "from transformers import AutoModel, AutoTokenizer; p='/app/classifier/.model-cache'; AutoTokenizer.from_pretrained('distilbert-base-uncased', cache_dir=p); AutoModel.from_pretrained('distilbert-base-uncased', cache_dir=p)"
WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --no-access-log"]

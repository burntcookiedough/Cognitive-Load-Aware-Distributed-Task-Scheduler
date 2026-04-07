FROM python:3.11-slim
WORKDIR /app
COPY shared/ ./shared/
COPY cluster-nodes/ ./
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE ${NODE_PORT:-8011}
CMD ["sh", "-c", "uvicorn worker:app --host 0.0.0.0 --port ${NODE_PORT:-8011}"]

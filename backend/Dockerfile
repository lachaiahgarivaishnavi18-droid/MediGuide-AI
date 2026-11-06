FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install --no-install-recommends -y libgomp1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements-lock.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY data/ ./data/
ENV PYTHONPATH=/app/backend
RUN python scripts/download_embedding_model.py
RUN useradd --create-home mediguide && chown -R mediguide:mediguide /app
USER mediguide
EXPOSE 8000
CMD ["python", "scripts/start_backend.py"]

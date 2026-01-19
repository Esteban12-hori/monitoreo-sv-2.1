FROM python:3.9-slim

WORKDIR /app

COPY src/server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

# Create data directory for SQLite
RUN mkdir -p data

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

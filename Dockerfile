# Stage 1: Build Frontend
FROM node:18 as frontend-build
WORKDIR /app/client
COPY src/client/package*.json ./
RUN npm install
COPY src/client ./
RUN npm run build

# Stage 2: Backend
FROM python:3.10-slim
WORKDIR /app

# Install dependencies
COPY src/server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY src/server /app/src/server
COPY config /app/config
# Copy built frontend to the location expected by main.py (../../frontend from app/main.py)
# main.py is in /app/src/server/app/main.py
# ../../.. is /app/src
# so we place frontend in /app/src/frontend
COPY --from=frontend-build /app/client/dist /app/src/frontend

# Create data directory
RUN mkdir -p /app/data

# Environment variables
ENV PYTHONPATH=/app
ENV ENV=production

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "src.server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

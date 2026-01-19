FROM python:3.9-slim

WORKDIR /app

# Install system dependencies if needed (psutil might need gcc)
# RUN apt-get update && apt-get install -y gcc python3-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Entrypoint script to handle configuration via Environment Variables
COPY docker_entrypoint.sh .
RUN chmod +x docker_entrypoint.sh

CMD ["./docker_entrypoint.sh"]

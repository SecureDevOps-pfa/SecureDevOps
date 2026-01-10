FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    docker.io \
    docker-compose \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/backend

# Copy backend code
COPY backend/ .

# Copy pipelines
COPY pipelines/ /workspace/pipelines/

# Copy runners
COPY runners/ /workspace/runners/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

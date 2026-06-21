FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements_docker.txt .
RUN pip install --no-cache-dir -r requirements_docker.txt

# Copy backend source code
COPY . /app/backend

# Make startup script executable
RUN chmod +x /app/backend/startup.sh

# Expose port
EXPOSE 8000

# Set entrypoint to run startup script
ENTRYPOINT ["/app/backend/startup.sh"]

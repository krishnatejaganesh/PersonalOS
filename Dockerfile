FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY core/ ./core/
COPY integrations/ ./integrations/

# Expose API port
EXPOSE 8080

# Default: run the API
CMD ["python", "-m", "core.api"]

FROM python:3.11-slim

# Install system dependencies for mitmproxy
RUN apt-get update && apt-get install -y --no-install-recommends \
    mitmproxy \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn

COPY . .

# Expose Web Interface (8000) and Local Proxy Engine (8080)
EXPOSE 8000
EXPOSE 8080

# Launch both proxy engine and dashboard manager
CMD ["sh", "-c", "mitmdump -s proxy_script.py --set block_global=false & uvicorn main:app --host 0.0.0.0 --port 8000"]

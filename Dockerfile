FROM python:3.11-slim

# Install minimal build tools for compiling Python wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install explicit layout modules and mitmproxy directly via PyPI
RUN pip install --no-cache-dir fastapi uvicorn mitmproxy

# Clean up build tools afterwards to keep the image slim
RUN apt-get purge -y --auto-remove gcc g++ libc6-dev

COPY . .

# Expose Web Interface (8000) and Local Proxy Engine (8080)
EXPOSE 8000
EXPOSE 8080

# Clean executable array wrapper handling OS signals cleanly
CMD ["sh", "-c", "mitmdump -s proxy_script.py --set block_global=false & uvicorn main:app --host 0.0.0.0 --port 8000"]

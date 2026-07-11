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

# Create a wrapper script that runs both processes with proper signal handling
RUN printf '#!/bin/sh\n\
mitmdump -s /app/proxy_script.py --set block_global=false --listen-host 0.0.0.0 &\n\
MITM_PID=$!\n\
uvicorn main:app --host 0.0.0.0 --port 8000 &\n\
UVICORN_PID=$!\n\
trap "kill $MITM_PID $UVICORN_PID 2>/dev/null; exit 0" SIGTERM SIGINT\n\
wait\n' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Expose Web Interface (8000) and Local Proxy Engine (8080)
EXPOSE 8000
EXPOSE 8080

# Use the wrapper script as entrypoint
CMD ["/app/entrypoint.sh"]

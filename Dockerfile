# KB MCP Server - Docker Image
# Multi-stage build för minimal image-storlek

FROM python:3.11-slim as builder

WORKDIR /app

# Installera dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

# Kopiera installerade paket
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Kopiera applikationskod
COPY . .

# Exponera port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Kör servern
CMD ["python", "kb_mcp_server.py", "--http", "--port", "8000"]

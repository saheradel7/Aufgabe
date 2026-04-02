# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY main.py .
COPY parser/ parser/

# Copy input data
COPY data/ data/

# Default: run the parser; output.json is written inside /app
CMD ["python", "main.py"]

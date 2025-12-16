# Dockerfile for Anomaly Analysis Agent Service
FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config.yaml .
COPY .env .
COPY create_anomaly_analysis_table.sql .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port for Cloud Run
EXPOSE 8080

# Run the anomaly analyzer
CMD ["python", "-m", "src.agent.anomaly_analyzer"]
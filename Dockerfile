# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for any Python packages)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV USE_MCP_BACKEND=true

# Cloud Run will set PORT environment variable, default to 8080
ENV PORT=8080

# Expose port (Cloud Run uses dynamic port via $PORT)
EXPOSE 8080

# Run uvicorn with backend.api:app
# Cloud Run requires binding to 0.0.0.0 and using $PORT
CMD uvicorn backend.api:app --host 0.0.0.0 --port $PORT

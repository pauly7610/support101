# Backend Dockerfile for FastAPI
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app code
COPY . .

# Expose port for Uvicorn
EXPOSE 8000

# API keys must be provided via env_file or runtime env — never hardcode
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

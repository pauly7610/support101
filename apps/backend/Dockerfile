# Backend Dockerfile for FastAPI
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app code
COPY . .

# Expose port for Uvicorn
EXPOSE 8000

# Use a mock Pinecone if running locally (optional: user can override)
ENV PINECONE_API_KEY=dummy-key
ENV PINECONE_ENVIRONMENT=mock

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

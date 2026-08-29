FROM python:3.13-slim

WORKDIR /app

# Install system deps for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY memory_service/ memory_service/

EXPOSE 8000
CMD ["uvicorn", "memory_service.main:app", "--host", "0.0.0.0", "--port", "8000"]

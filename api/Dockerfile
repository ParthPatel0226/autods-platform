FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer caching)
COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt

# Copy the api package
COPY api/ /app/api/

# Copy backend modules that api/ imports from
COPY core/ /app/core/
COPY serving/ /app/serving/
COPY agents/ /app/agents/
COPY data_connectors/ /app/data_connectors/
COPY domains/ /app/domains/
COPY evaluation/ /app/evaluation/
COPY validation/ /app/validation/
COPY explainability/ /app/explainability/
COPY reports/ /app/reports/
COPY logging_audit/ /app/logging_audit/
COPY session/ /app/session/
COPY configs/ /app/configs/

# Set Python path so all modules resolve from /app
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

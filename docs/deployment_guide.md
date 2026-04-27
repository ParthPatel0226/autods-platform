# Deployment Guide

## Prerequisites

- Python 3.11+
- An Anthropic API key (`ANTHROPIC_API_KEY`)
- Docker (for containerized deployment)

## Local Development

```bash
git clone https://github.com/youruser/autods-platform.git
cd autods-platform

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install
make setup                  # deps + sample data + databases

# Configure
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY=sk-ant-...

# Run dashboard
make run                    # Streamlit at http://localhost:8501
#                          # Opens landing page with hero section, sample datasets, and theme toggle
```

**First Launch**: The landing page displays a professional dark-gradient hero banner with floating stat pills, a three-card feature showcase, drag-and-drop upload zone, and a sample dataset selector. Choose **Light** or **Dark** mode via the sidebar toggle.

## Docker Compose (Recommended for Production)

The `docker-compose.yml` orchestrates three services:

| Service | Port | Purpose |
|---------|------|---------|
| dashboard | 8501 | Streamlit web application |
| api | 8000 | FastAPI prediction endpoint |
| mlflow | 5000 | MLflow experiment tracking (optional) |

```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f dashboard

# Stop
docker compose down
```

### Environment Variables

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
AUTODS_DUCKDB_PATH=/app/data/warehouse.duckdb
AUTODS_SQLITE_PATH=/app/sessions/autods.db
MLFLOW_TRACKING_URI=/app/mlruns
```

### Persistent Volumes

Docker Compose mounts these directories:

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `./data` | `/app/data` | Uploaded datasets, DuckDB warehouse |
| `./sessions` | `/app/sessions` | Saved sessions (SQLite) |
| `./outputs` | `/app/outputs` | Generated reports |
| `./mlruns` | `/app/mlruns` | MLflow experiment data |
| `./logs` | `/app/logs` | Structured logs |

## Streamlit Community Cloud (Free)

1. Push project to a public GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set entry point: `dashboard/app.py`
5. Add secrets in Streamlit settings:
   ```toml
   # .streamlit/secrets.toml
   ANTHROPIC_API_KEY = "sk-ant-api03-..."
   ```

**Limitations**: Streamlit Cloud has memory limits (~1GB). Large datasets may require the Docker deployment.

## HuggingFace Spaces (Free)

1. Create a new Space with **Streamlit** SDK
2. Push project files
3. Add `ANTHROPIC_API_KEY` as a secret in Space settings
4. HuggingFace auto-detects `requirements.txt` and builds

## Individual Docker Containers

### Dashboard Only

```bash
docker build -t autods-dashboard -f Dockerfile.dashboard .
docker run -p 8501:8501 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -v $(pwd)/data:/app/data \
  autods-dashboard
```

### Prediction API Only

```bash
docker build -t autods-api -f serving/Dockerfile .
docker run -p 8000:8000 \
  -e AUTODS_MODEL_PATH=/app/artifacts/best_model.joblib \
  -v $(pwd)/artifacts:/app/artifacts \
  autods-api
```

## Production Checklist

- [ ] Set `ANTHROPIC_API_KEY` via secret manager (not plaintext)
- [ ] Configure persistent volumes for data, sessions, mlruns
- [ ] Set up reverse proxy (nginx/Caddy) with HTTPS
- [ ] Enable rate limiting on the prediction API
- [ ] Configure log rotation for `./logs/`
- [ ] Set up monitoring (health check at `/health`)
- [ ] Back up `sessions/` and `mlruns/` directories
- [ ] Review `serving/api.py` for authentication (currently open)
- [ ] Test with representative datasets before going live

## Scaling Considerations

| Component | Scaling Strategy |
|-----------|-----------------|
| Dashboard | Single instance (Streamlit is stateful per session) |
| Prediction API | Horizontal: multiple Uvicorn workers or replicas |
| MLflow | Separate server with PostgreSQL backend for teams |
| DuckDB | Single-writer; for concurrent access, use PostgreSQL |

## Troubleshooting

**"Model not loaded"**: Train a model via the dashboard first, or set `AUTODS_MODEL_PATH` to an existing `.joblib` file.

**Out of memory**: Large datasets (>1M rows) may exceed RAM. Use `nrows` parameter in upload to sample, or deploy on a larger instance.

**Slow startup**: First run downloads NLTK data, initializes ChromaDB, and compiles models. Subsequent starts are faster.

**Port conflicts**: Change ports in `docker-compose.yml` or use `-p` flag:
```bash
docker run -p 9501:8501 autods-dashboard
```

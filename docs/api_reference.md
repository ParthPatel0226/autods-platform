# API Reference

AutoDS exposes a FastAPI prediction API for serving trained models.

## Base URL

```
http://localhost:8000
```

## Endpoints

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true
}
```

### GET /info

Return model metadata (algorithm, problem type, features, domain).

**Response:**
```json
{
  "algorithm": "xgboost",
  "problem_type": "classification",
  "trained_at": "2026-04-24T10:30:00Z",
  "features": 15,
  "domain": "healthcare",
  "feature_names": ["age", "bmi", "blood_pressure", "..."]
}
```

### POST /predict

Single sample prediction.

**Request:**
```json
{
  "features": {
    "age": 45,
    "income": 65000,
    "tenure_months": 24
  },
  "include_shap": false
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "prediction": 1,
    "confidence": 0.73,
    "probabilities": {"0": 0.27, "1": 0.73},
    "shap_values": null
  }
}
```

When `include_shap: true`:
```json
{
  "success": true,
  "result": {
    "prediction": 1,
    "confidence": 0.73,
    "probabilities": {"0": 0.27, "1": 0.73},
    "shap_values": {
      "tenure_months": -0.15,
      "income": 0.08,
      "age": 0.03
    }
  }
}
```

### POST /predict/batch

Batch prediction for multiple samples (max 10,000).

**Request:**
```json
{
  "samples": [
    {"age": 45, "income": 65000},
    {"age": 32, "income": 42000}
  ],
  "include_shap": false
}
```

**Response:**
```json
{
  "success": true,
  "results": [
    {"prediction": 1, "confidence": 0.73, "probabilities": {"0": 0.27, "1": 0.73}},
    {"prediction": 0, "confidence": 0.88, "probabilities": {"0": 0.88, "1": 0.12}}
  ],
  "count": 2
}
```

### POST /reload

Force reload model from disk (after retraining).

**Response:**
```json
{
  "status": "cache_cleared",
  "message": "Model will be reloaded on next prediction."
}
```

## Error Responses

All errors return:
```json
{
  "detail": "Error description"
}
```

| Status | Meaning |
|--------|---------|
| 422 | Missing or invalid features |
| 500 | Internal prediction error |
| 503 | Model not loaded (train a model first) |

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `AUTODS_MODEL_PATH` | `artifacts/best_model.joblib` | Path to trained model |

## Running the API

```bash
# Development
make serve

# Production
uvicorn serving.api:app --host 0.0.0.0 --port 8000

# Docker
docker build -t autods-api -f serving/Dockerfile .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=sk-... autods-api
```

## Python Client Example

```python
import requests

# Single prediction
resp = requests.post("http://localhost:8000/predict", json={
    "features": {"age": 45, "income": 65000, "tenure_months": 24},
    "include_shap": True
})
result = resp.json()["result"]
print(f"Prediction: {result['prediction']}, Confidence: {result['confidence']}")

# Batch prediction
resp = requests.post("http://localhost:8000/predict/batch", json={
    "samples": [
        {"age": 45, "income": 65000},
        {"age": 32, "income": 42000},
    ]
})
for r in resp.json()["results"]:
    print(f"Prediction: {r['prediction']}")
```

## Interactive Docs

FastAPI auto-generates interactive documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

# Zeus Flask API - Render Deployment

## Quick Deploy to Render

### Option 1: Using render.yaml (Blueprint)

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New" → "Blueprint"
4. Connect your GitHub repository
5. Render will detect `render.yaml` and configure the service automatically
6. Add your `MONGO_URI` environment variable in the Render dashboard:
   - Go to your service → Environment
   - Add: `MONGO_URI` = your MongoDB connection string

### Option 2: Manual Web Service Creation

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: zeus-api (or your preferred name)
   - **Region**: Oregon (or your preferred region)
   - **Branch**: main
   - **Root Directory**: API
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn api:app -c gunicorn.conf.py`
5. Add Environment Variables:
   - `MONGO_URI`: Your MongoDB Atlas connection string
   - `MONGO_DB`: zeus_multi
   - `TTL_SECONDS`: 10800
   - `PYTHON_VERSION`: 3.12.0
6. Click "Create Web Service"

## Environment Variables

Required:

- `MONGO_URI`: MongoDB Atlas connection string (must be set in Render dashboard)

Optional:

- `MONGO_DB`: Database name (default: zeus_multi)
- `TTL_SECONDS`: Time to live for metrics in seconds (default: 10800 = 3 hours)

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /ingest` - Ingest telemetry data
- `GET /metrics/recent?client_id=X&limit=200` - Get recent metrics
- `GET /predictions/recent?client_id=X&limit=100` - Get recent predictions

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (uses .env file)
python api.py

# Or with gunicorn
gunicorn api:app -c gunicorn.conf.py
```

## Production Notes

- The API uses Gunicorn as the production WSGI server
- CORS is enabled for all origins
- MongoDB time-series collections are used for efficient metric storage
- Auto-scaling is configured based on CPU count
- Health checks are configured at `/health`

## Security

- Never commit `.env` file to git
- Set `MONGO_URI` as environment variable in Render dashboard
- Use MongoDB Atlas IP whitelist (allow Render's IP ranges or use 0.0.0.0/0 for simplicity)

## Monitoring

Check logs in Render dashboard:

- Go to your service → Logs
- Monitor for errors or warnings
- TTL index warnings are non-critical for certain MongoDB tiers

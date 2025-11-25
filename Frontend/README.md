# PdM Dashboard (React + Tailwind + Recharts)

A real-time predictive maintenance dashboard for monitoring industrial equipment sensor data and failure predictions.

## Features
- Device selector (fetches /api/devices if available, fallback manual input)
- Real-time sensor stream (polls /api/latest/{device_id})
- Maintains a sliding 60-step window client-side
- Calls /api/predict/fusion when window is ready (POST) to get fused risk
- Shows device list, real-time charts for sensors, risk gauge, AE anomaly spikes, failure countdown, and alerts

## Quick start (Vite + React)

### 1) Create project
```bash
npm create vite@latest pdm-dashboard -- --template react
cd pdm-dashboard
```

### 2) Install dependencies
```bash
npm install tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install recharts dayjs
```

### 3) Configure Tailwind (tailwind.config.cjs)
```javascript
module.exports = {
  content: ["./index.html","./src/**/*.{js,jsx,ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

### 4) Add Tailwind directives to src/index.css
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 5) Replace src/App.jsx with the dashboard component and run:
```bash
npm run dev
```

## Backend API Endpoints Expected

The dashboard expects these endpoints from your FastAPI backend:

- **GET /api/devices** → returns `["device_id1","device_id2", ...]` (optional)
- **GET /api/latest/{device_id}** → returns latest sensor doc: `{ device_id, timestamp, temperature, vibration, rpm, humidity, label }`
- **POST /api/predict/fusion** → accepts `{ window: [[...],...], agg: {...} }` and returns fusion scores `{ fused_risk, failure_prob_lstm, prob_failure_rf, ae_score, ae_scaled, health_score }`

If `/api/devices` is not available, you can input a device ID manually.

## Dashboard Features

### Real-time Monitoring
- Live sensor data visualization (temperature, vibration, RPM, humidity)
- 60-sample sliding window for analysis
- Automatic polling every 2 seconds

### Predictive Analytics
- Fused risk score combining LSTM and Random Forest models
- Autoencoder anomaly detection
- Failure countdown estimation
- Alert system with cooldown periods

### User Interface
- Device selection and management
- Multi-sensor time series charts
- Risk gauges and metrics
- Alert log with severity levels
- Responsive design with Tailwind CSS
import React, { useEffect, useState, useRef } from "react";
import dayjs from "dayjs";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts";

// Default export React component for preview
export default function PdMDashboard() {
  // UI state
  const [devices, setDevices] = useState([]);
  const [deviceId, setDeviceId] = useState("");
  const [connected, setConnected] = useState(false);
  const [stream, setStream] = useState([]); // array of recent records
  const streamRef = useRef([]);
  const [windowSize] = useState(60);
  const [fusion, setFusion] = useState(null);
  const [aeHistory, setAeHistory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [cooldown, setCooldown] = useState({});

  // polling intervals
  const POLL_MS = 2000; // 2s poll
  const FUSION_COOLDOWN_MS = 60_000; // 60s cooldown per device for alerts

  useEffect(() => {
    // try fetch device list
    fetch("/api/devices")
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d)) setDevices(d);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    let poller;
    if (connected && deviceId) {
      // start polling latest
      poller = setInterval(async () => {
        try {
          const res = await fetch(`/api/latest/${encodeURIComponent(deviceId)}`);
          if (!res.ok) return;
          const doc = await res.json();
          // normalize fields
          const rec = {
            timestamp: doc.timestamp || doc._id?.getTimestamp || new Date().toISOString(),
            temperature: doc.temperature ?? null,
            vibration: doc.vibration ?? null,
            rpm: doc.rpm ?? null,
            humidity: doc.humidity ?? null,
          };
          pushRecord(rec);
        } catch (e) {
          // ignore errors
        }
      }, POLL_MS);
    }
    return () => clearInterval(poller);
  }, [connected, deviceId]);

  function pushRecord(rec) {
    // maintain ref for fast updates
    const arr = streamRef.current.slice();
    arr.push(rec);
    // keep last windowSize * 4 (a buffer)
    if (arr.length > windowSize * 4) arr.splice(0, arr.length - windowSize * 4);
    streamRef.current = arr;
    setStream(arr.slice(-windowSize));

    // if we have enough samples, call fusion
    const curWindow = arr.slice(-windowSize);
    if (curWindow.length >= windowSize) {
      callFusion(curWindow);
    }
  }

  async function callFusion(window) {
    // compute simple aggregates for RF - mean values per sensor
    const agg = {};
    const keys = ["temperature", "vibration", "rpm", "humidity"];
    keys.forEach((k) => {
      const vals = window.map((r) => (r[k] != null ? r[k] : NaN)).filter((v) => !Number.isNaN(v));
      agg[`${k}_mean`] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
      agg[`${k}_std`] = vals.length > 1 ? Math.sqrt(vals.map(v => (v-agg[`${k}_mean`])**2).reduce((a,b)=>a+b,0)/(vals.length-1)) : 0;
    });
    // POST to API
    try {
      const body = { window: window.map((r) => [r.temperature ?? 0, r.vibration ?? 0, r.rpm ?? 0, r.humidity ?? 0]), agg };
      const res = await fetch("/api/predict/fusion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) return;
      const j = await res.json();
      setFusion(j);
      // AE history
      setAeHistory((h) => [...h.slice(-99), { t: new Date().toISOString(), ae: j.ae_scaled }]);
      checkAlerts(j);
    } catch (e) {
      // console.warn(e)
    }
  }

  function checkAlerts(j) {
    const now = Date.now();
    const deviceCooldown = cooldown[deviceId] || 0;
    if (now < deviceCooldown) return; // still cooling down
    // thresholds
    if (j.fused_risk >= 0.75) {
      // critical
      const alert = { id: `${deviceId}_${now}`, level: "critical", text: `CRITICAL risk ${j.fused_risk.toFixed(2)} on ${deviceId}`, time: new Date().toISOString() };
      setAlerts((a) => [alert, ...a].slice(0, 50));
      setCooldown((c) => ({ ...c, [deviceId]: now + FUSION_COOLDOWN_MS }));
    } else if (j.fused_risk >= 0.5) {
      const alert = { id: `${deviceId}_${now}`, level: "warning", text: `Warning risk ${j.fused_risk.toFixed(2)} on ${deviceId}`, time: new Date().toISOString() };
      setAlerts((a) => [alert, ...a].slice(0, 50));
      setCooldown((c) => ({ ...c, [deviceId]: now + FUSION_COOLDOWN_MS / 2 }));
    }
  }

  // failure countdown heuristic: estimate time until failure if we have recent risk increase slope
  function estimateCountdown() {
    if (!aeHistory.length || !fusion) return null;
    // simple heuristic: if fused_risk > 0.5, countdown = (1 - fused_risk)/slope * POLL_MS
    const recent = aeHistory.slice(-6).map((d, i) => ({ t: i, v: d.ae }));
    if (recent.length < 3) return null;
    const xs = recent.map((d) => d.t);
    const ys = recent.map((d) => d.v);
    const n = xs.length;
    const xmean = xs.reduce((a,b)=>a+b,0)/n;
    const ymean = ys.reduce((a,b)=>a+b,0)/n;
    const num = xs.map((x,i)=> (x - xmean)*(ys[i]-ymean)).reduce((a,b)=>a+b,0);
    const den = xs.map(x => (x - xmean)*(x - xmean)).reduce((a,b)=>a+b,0) || 1;
    const slope = num / den;
    if (slope <= 0) return null;
    const timeStepsNeeded = (1 - fusion.fused_risk) / slope; // very rough
    const ms = timeStepsNeeded * POLL_MS;
    if (!isFinite(ms) || ms < 0) return null;
    return Math.round(ms / 1000); // seconds
  }

  // UI helpers
  const sensorSeries = stream.map((s) => ({
    t: dayjs(s.timestamp).format("HH:mm:ss"),
    temperature: s.temperature,
    vibration: s.vibration,
    rpm: s.rpm,
    humidity: s.humidity,
  }));

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        <header className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">PdM Dashboard</h1>
          <div className="flex items-center gap-3">
            <select value={deviceId} onChange={(e)=>{setDeviceId(e.target.value); setConnected(false);}} className="border px-2 py-1 rounded">
              <option value="">-- Select device --</option>
              {devices.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
            <input placeholder="Or enter device id" className="border px-2 py-1 rounded" onBlur={(e)=>{ if(e.target.value) setDeviceId(e.target.value); }} />
            <button className={`px-3 py-1 rounded ${connected? 'bg-red-500 text-white' : 'bg-green-600 text-white'}`} onClick={()=>setConnected(c=>!c)}>{connected? 'Stop' : 'Connect'}</button>
          </div>
        </header>

        <main className="grid grid-cols-3 gap-4">
          <section className="col-span-1 bg-white p-4 rounded shadow">
            <h2 className="font-semibold mb-2">Devices</h2>
            <div className="text-sm text-gray-600 mb-2">Known devices (from API)</div>
            <ul className="space-y-1 max-h-64 overflow-auto">
              {devices.length ? devices.map(d => (
                <li key={d} className={`p-2 rounded cursor-pointer hover:bg-gray-100 ${d===deviceId? 'bg-gray-100 font-medium' : ''}`} onClick={()=>{setDeviceId(d); setConnected(true);}}>{d}</li>
              )) : <li className="text-xs text-gray-500">No device list available — enter id manually</li>}
            </ul>
            <div className="mt-4">
              <h3 className="font-semibold">Alert log</h3>
              <div className="max-h-48 overflow-auto text-sm mt-2">
                {alerts.length ? alerts.map(a => (
                  <div key={a.id} className={`p-2 mb-1 rounded ${a.level==='critical'? 'bg-red-100 border-l-4 border-red-600' : 'bg-yellow-50 border-l-4 border-yellow-400'}`}>
                    <div className="text-xs text-gray-500">{dayjs(a.time).format('HH:mm:ss')}</div>
                    <div className="text-sm">{a.text}</div>
                  </div>
                )) : <div className="text-xs text-gray-500">No alerts</div>}
              </div>
            </div>
          </section>

          <section className="col-span-2 bg-white p-4 rounded shadow">
            <div className="flex items-start justify-between">
              <h2 className="font-semibold">Live Sensor Stream</h2>
              <div className="text-right">
                <div className="text-sm text-gray-500">Device: <span className="font-medium">{deviceId || '—'}</span></div>
                <div className="text-xs text-gray-400">Samples: {stream.length}</div>
              </div>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-3">
              <div className="h-48 bg-white border rounded p-2">
                <ResponsiveContainer width="100%" height={160}>
                  <LineChart data={sensorSeries}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="t" minTickGap={20} />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="temperature" stroke="#ef4444" dot={false} />
                    <Line type="monotone" dataKey="vibration" stroke="#f59e0b" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="h-48 bg-white border rounded p-2">
                <ResponsiveContainer width="100%" height={160}>
                  <LineChart data={sensorSeries}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="t" minTickGap={20} />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="rpm" stroke="#3b82f6" dot={false} />
                    <Line type="monotone" dataKey="humidity" stroke="#10b981" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-3">
              <div className="p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-500">Fused Risk</div>
                <div className="text-2xl font-bold">{fusion ? fusion.fused_risk.toFixed(2) : '—'}</div>
                <div className="text-sm text-gray-500">LSTM: {fusion ? fusion.failure_prob_lstm.toFixed(2) : '—'}</div>
                <div className="text-sm text-gray-500">RF fail prob: {fusion ? fusion.prob_failure_rf.toFixed(2) : '—'}</div>
              </div>

              <div className="p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-500">AE Anomaly (scaled)</div>
                <div className="text-xl font-bold">{fusion ? fusion.ae_scaled.toFixed(3) : '—'}</div>
                <div className="text-sm text-gray-500">Raw AE: {fusion ? fusion.ae_score.toExponential(2) : '—'}</div>
              </div>

              <div className="p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-500">Failure countdown (est)</div>
                <div className="text-xl font-bold">{estimateCountdown() ? `${estimateCountdown()}s` : 'N/A'}</div>
                <div className="text-sm text-gray-500">Heuristic estimate</div>
              </div>
            </div>

            <div className="mt-4">
              <h3 className="font-semibold">AE anomaly spikes (history)</h3>
              <div className="h-36 mt-2 bg-white border rounded p-2">
                <ResponsiveContainer width="100%" height={120}>
                  <LineChart data={aeHistory.map((d,i)=>({ t: i, ae: d.ae }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="t" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="ae" stroke="#8b5cf6" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

          </section>

        </main>
      </div>
    </div>
  );
}
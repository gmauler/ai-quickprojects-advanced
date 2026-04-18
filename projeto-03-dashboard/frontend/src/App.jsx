import { useState, useEffect } from "react"
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"
import axios from "axios"

const API = "http://localhost:8000"

function MetricCard({ label, value, sub }) {
  return (
    <div style={{
      background: "#f9f9f9", borderRadius: 12, padding: "16px 20px",
      border: "1px solid #eee", minWidth: 140
    }}>
      <div style={{ fontSize: 12, color: "#999", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 600, color: "#111" }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: "#bbb", marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

export default function App() {
  const [summary, setSummary] = useState(null)
  const [history, setHistory] = useState([])
  const [prompt, setPrompt] = useState("")
  const [response, setResponse] = useState("")
  const [loading, setLoading] = useState(false)

  async function loadData() {
    try {
      const [r1, r2] = await Promise.all([
        axios.get(`${API}/analytics/summary`),
        axios.get(`${API}/analytics/history`)
      ])
      setSummary(r1.data)
      setHistory(r2.data)
    } catch (e) {
      console.error("Failed to load analytics:", e)
    }
  }

  // Load data on mount and refresh every 5 seconds
  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [])

  async function send() {
    if (!prompt.trim()) return
    setLoading(true)
    setResponse("")
    try {
      const res = await axios.post(`${API}/chat`, { prompt })
      setResponse(res.data.response)
      loadData()
    } catch (e) {
      setResponse("Error contacting the server.")
    }
    setLoading(false)
  }

  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 900, margin: "0 auto", padding: 24 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 24 }}>
        Claude Analytics Dashboard
      </h1>

      <div style={{ display: "flex", gap: 12, marginBottom: 32, flexWrap: "wrap" }}>
        <MetricCard label="Total calls" value={summary?.total_calls ?? "—"} />
        <MetricCard label="Total tokens" value={summary?.total_tokens?.toLocaleString() ?? "—"} />
        <MetricCard label="Avg latency" value={summary ? `${summary.avg_latency_ms}ms` : "—"} />
        <MetricCard
          label="Total cost"
          value={summary ? `$${summary.total_cost_usd.toFixed(4)}` : "—"}
          sub="USD estimated"
        />
      </div>

      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 15, fontWeight: 500, marginBottom: 12, color: "#555" }}>
          Latency per call (ms)
        </h2>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={history}>
            <XAxis dataKey="time" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="latency" stroke="#7F77DD" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 15, fontWeight: 500, marginBottom: 12, color: "#555" }}>
          Tokens per call
        </h2>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={history}>
            <XAxis dataKey="time" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="tokens" fill="#1D9E75" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ borderTop: "1px solid #eee", paddingTop: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 500, marginBottom: 12, color: "#555" }}>
          Test a call
        </h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <input
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => e.key === "Enter" && send()}
            placeholder="Type a prompt..."
            style={{
              flex: 1, padding: "10px 14px", borderRadius: 8,
              border: "1px solid #ddd", fontSize: 14, outline: "none"
            }}
          />
          <button
            onClick={send}
            disabled={loading}
            style={{
              padding: "10px 20px", background: "#111", color: "#fff",
              border: "none", borderRadius: 8, cursor: "pointer", fontSize: 14
            }}
          >
            {loading ? "..." : "Send"}
          </button>
        </div>
        {response && (
          <div style={{
            background: "#f9f9f9", padding: 16, borderRadius: 8,
            fontSize: 14, lineHeight: 1.6, color: "#333",
            border: "1px solid #eee", whiteSpace: "pre-wrap"
          }}>
            {response}
          </div>
        )}
      </div>
    </div>
  )
}
import { useState, useEffect } from "react"
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"
import axios from "axios"

const API = "http://localhost:8000"

// Componente de card de métrica — reutilizável
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
  // useState guarda dados que quando mudam re-renderizam o componente
  const [resumo, setResumo] = useState(null)
  const [historico, setHistorico] = useState([])
  const [prompt, setPrompt] = useState("")
  const [resposta, setResposta] = useState("")
  const [loading, setLoading] = useState(false)

  // Função para ir buscar dados ao backend
  async function carregarDados() {
    try {
      const [r1, r2] = await Promise.all([
        axios.get(`${API}/analytics/resumo`),
        axios.get(`${API}/analytics/historico`)
      ])
      setResumo(r1.data)
      setHistorico(r2.data)
    } catch (e) {
      console.error("Erro ao carregar dados:", e)
    }
  }

  // useEffect corre quando o componente é montado
  // O intervalo actualiza os dados a cada 5 segundos
  useEffect(() => {
    carregarDados()
    const intervalo = setInterval(carregarDados, 5000)
    return () => clearInterval(intervalo) // cleanup quando componente é desmontado
  }, [])

  async function enviar() {
    if (!prompt.trim()) return
    setLoading(true)
    setResposta("")
    try {
      const res = await axios.post(`${API}/chat`, { prompt })
      setResposta(res.data.resposta)
      carregarDados() // actualiza métricas após cada chamada
    } catch (e) {
      setResposta("Erro ao contactar o servidor.")
    }
    setLoading(false)
  }

  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 900, margin: "0 auto", padding: 24 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 24 }}>
        Claude Analytics Dashboard
      </h1>

      {/* Cards de métricas */}
      <div style={{ display: "flex", gap: 12, marginBottom: 32, flexWrap: "wrap" }}>
        <MetricCard
          label="Total de chamadas"
          value={resumo?.total_chamadas ?? "—"}
        />
        <MetricCard
          label="Total de tokens"
          value={resumo?.total_tokens?.toLocaleString() ?? "—"}
        />
        <MetricCard
          label="Latência média"
          value={resumo ? `${resumo.latencia_media_ms}ms` : "—"}
        />
        <MetricCard
          label="Custo total"
          value={resumo ? `$${resumo.custo_total_usd.toFixed(4)}` : "—"}
          sub="USD estimado"
        />
      </div>

      {/* Gráfico de latência */}
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 15, fontWeight: 500, marginBottom: 12, color: "#555" }}>
          Latência por chamada (ms)
        </h2>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={historico}>
            <XAxis dataKey="hora" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="latencia" stroke="#7F77DD" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Gráfico de tokens */}
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 15, fontWeight: 500, marginBottom: 12, color: "#555" }}>
          Tokens por chamada
        </h2>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={historico}>
            <XAxis dataKey="hora" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="tokens" fill="#1D9E75" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Caixa de chat */}
      <div style={{ borderTop: "1px solid #eee", paddingTop: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 500, marginBottom: 12, color: "#555" }}>
          Testar chamada
        </h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <input
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => e.key === "Enter" && enviar()}
            placeholder="Escreve um prompt..."
            style={{
              flex: 1, padding: "10px 14px", borderRadius: 8,
              border: "1px solid #ddd", fontSize: 14, outline: "none"
            }}
          />
          <button
            onClick={enviar}
            disabled={loading}
            style={{
              padding: "10px 20px", background: "#111", color: "#fff",
              border: "none", borderRadius: 8, cursor: "pointer", fontSize: 14
            }}
          >
            {loading ? "..." : "Enviar"}
          </button>
        </div>
        {resposta && (
          <div style={{
            background: "#f9f9f9", padding: 16, borderRadius: 8,
            fontSize: 14, lineHeight: 1.6, color: "#333",
            border: "1px solid #eee", whiteSpace: "pre-wrap"
          }}>
            {resposta}
          </div>
        )}
      </div>
    </div>
  )
}
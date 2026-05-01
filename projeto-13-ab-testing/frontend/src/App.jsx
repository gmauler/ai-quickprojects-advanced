import { useState, useEffect } from "react"
import Editor from "@monaco-editor/react"

const API = "http://localhost:8004"

const DEFAULT_A = `You are a helpful assistant. Answer clearly and concisely.`

const DEFAULT_B = `You are an expert assistant. Structure your response with:
1. Direct answer in the first sentence
2. Supporting details with bullet points
3. A practical example when relevant
Always be specific and actionable.`

const DEFAULT_INPUT = `What are the main causes of high latency in a REST API?`

function MetricBadge({ label, value, highlight }) {
  return (
    <div style={{
      background: highlight ? "#E1F5EE" : "#f4f4f4",
      borderRadius: 8, padding: "6px 12px",
      display: "flex", flexDirection: "column", alignItems: "center"
    }}>
      <span style={{ fontSize: 10, color: "#666", marginBottom: 2 }}>{label}</span>
      <span style={{
        fontSize: 14, fontWeight: 600,
        color: highlight ? "#085041" : "#111"
      }}>{value}</span>
    </div>
  )
}

function ResponsePanel({ label, result, onVote, voted, winner }) {
  const isWinner = winner === label
  const isLoser = winner && winner !== label

  return (
    <div style={{
      flex: 1, border: `2px solid ${isWinner ? "#1D9E75" : isLoser ? "#eee" : "#eee"}`,
      borderRadius: 12, padding: 16, opacity: isLoser ? 0.6 : 1,
      transition: "all 0.2s"
    }}>
      <div style={{
        display: "flex", alignItems: "center",
        gap: 8, marginBottom: 12
      }}>
        <span style={{
          fontWeight: 700, fontSize: 16,
          color: isWinner ? "#1D9E75" : "#1a1a1a"
        }}>
          Prompt {label}
        </span>
        {isWinner && (
          <span style={{
            fontSize: 11, background: "#E1F5EE", color: "#085041",
            padding: "2px 8px", borderRadius: 20, fontWeight: 500
          }}>Winner</span>
        )}
        {result && (
          <div style={{ display: "flex", gap: 8, marginLeft: "auto" }}>
            <MetricBadge label="tokens" value={result.total_tokens} />
            <MetricBadge label="latency" value={`${result.latency_ms}ms`} />
            <MetricBadge label="cost" value={`$${result.cost_usd}`} />
          </div>
        )}
      </div>

      {result ? (
        <>
          <div style={{
            fontSize: 13, lineHeight: 1.7, color: "#222",
            whiteSpace: "pre-wrap", marginBottom: 14,
            maxHeight: 300, overflowY: "auto",
            padding: "10px 12px", background: "#fafafa",
            borderRadius: 8, border: "1px solid #eee"
          }}>
            {result.text}
          </div>
          {!voted && (
            <button
              onClick={() => onVote(label)}
              style={{
                width: "100%", padding: "8px 0",
                background: "#1a1a1a", color: "#fff",
                border: "none", borderRadius: 8,
                fontSize: 13, cursor: "pointer"
              }}
            >
              Vote for {label}
            </button>
          )}
        </>
      ) : (
        <div style={{
          height: 120, display: "flex", alignItems: "center",
          justifyContent: "center", color: "#bbb", fontSize: 13
        }}>
          Run the experiment to see results
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [promptA, setPromptA] = useState(DEFAULT_A)
  const [promptB, setPromptB] = useState(DEFAULT_B)
  const [inputText, setInputText] = useState(DEFAULT_INPUT)
  const [results, setResults] = useState(null)
  const [running, setRunning] = useState(false)
  const [winner, setWinner] = useState(null)
  const [history, setHistory] = useState([])
  const [tab, setTab] = useState("experiment")

  async function loadHistory() {
    try {
      const res = await fetch(`${API}/history`)
      setHistory(await res.json())
    } catch (e) {}
  }

  useEffect(() => { loadHistory() }, [])

  async function runExperiment() {
    setRunning(true)
    setResults(null)
    setWinner(null)
    try {
      const res = await fetch(`${API}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input_text: inputText,
          prompt_a: promptA,
          prompt_b: promptB
        })
      })
      setResults(await res.json())
    } catch (e) {
      console.error(e)
    }
    setRunning(false)
  }

  async function vote(label) {
    setWinner(label)
    if (!results) return
    await fetch(`${API}/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input_text: inputText,
        prompt_a: promptA,
        prompt_b: promptB,
        response_a: results.a,
        response_b: results.b,
        winner: label
      })
    })
    loadHistory()
  }

  const tabStyle = (t) => ({
    padding: "8px 16px", border: "none", cursor: "pointer",
    background: "transparent", fontSize: 14, fontWeight: 500,
    borderBottom: tab === t ? "2px solid #1a1a1a" : "2px solid transparent",
    color: tab === t ? "#1a1a1a" : "#999"
  })

  return (
    <>
      <style>{`* { margin: 0; padding: 0; box-sizing: border-box; } body { font-family: system-ui, sans-serif; background: #fafafa; }`}</style>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: 24 }}>

        <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>
          Prompt A/B Testing
        </h1>
        <p style={{ fontSize: 14, color: "#666", marginBottom: 24 }}>
          Compare two system prompts side by side with the same input
        </p>

        <div style={{ borderBottom: "1px solid #eee", marginBottom: 24, display: "flex", gap: 4 }}>
          <button style={tabStyle("experiment")} onClick={() => setTab("experiment")}>Experiment</button>
          <button style={tabStyle("history")} onClick={() => { setTab("history"); loadHistory() }}>
            History ({history.length})
          </button>
        </div>

        {tab === "experiment" && (
          <>
            {/* Prompt editors */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
              {[["A", promptA, setPromptA], ["B", promptB, setPromptB]].map(([label, value, setter]) => (
                <div key={label}>
                  <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 6, color: "#333" }}>
                    System Prompt {label}
                  </div>
                  <div style={{ border: "1px solid #ddd", borderRadius: 8, overflow: "hidden" }}>
                    <Editor
                      height="160px"
                      defaultLanguage="markdown"
                      value={value}
                      onChange={v => setter(v || "")}
                      options={{
                        minimap: { enabled: false },
                        lineNumbers: "off",
                        wordWrap: "on",
                        fontSize: 13,
                        scrollBeyondLastLine: false,
                        renderLineHighlight: "none",
                        overviewRulerLanes: 0
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Input */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 6, color: "#333" }}>
                User Input (same for both)
              </div>
              <textarea
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                rows={3}
                style={{
                  width: "100%", padding: "10px 14px",
                  border: "1px solid #ddd", borderRadius: 8,
                  fontSize: 13, resize: "vertical", outline: "none",
                  fontFamily: "system-ui"
                }}
              />
            </div>

            <button
              onClick={runExperiment}
              disabled={running}
              style={{
                padding: "10px 28px", background: running ? "#999" : "#1a1a1a",
                color: "#fff", border: "none", borderRadius: 8,
                fontSize: 14, cursor: running ? "not-allowed" : "pointer",
                marginBottom: 24
              }}
            >
              {running ? "Running both prompts..." : "Run Experiment"}
            </button>

            {/* Results */}
            <div style={{ display: "flex", gap: 16 }}>
              <ResponsePanel label="A" result={results?.a} onVote={vote} voted={!!winner} winner={winner} />
              <ResponsePanel label="B" result={results?.b} onVote={vote} voted={!!winner} winner={winner} />
            </div>

            {winner && results && (
              <div style={{
                marginTop: 16, padding: "12px 16px",
                background: "#E1F5EE", borderRadius: 8,
                fontSize: 13, color: "#085041"
              }}>
                You voted for Prompt <strong>{winner}</strong>.
                Tokens: A={results.a.total_tokens} vs B={results.b.total_tokens} |
                Latency: A={results.a.latency_ms}ms vs B={results.b.latency_ms}ms |
                Cost: A=${results.a.cost_usd} vs B=${results.b.cost_usd}
              </div>
            )}
          </>
        )}

        {tab === "history" && (
          <div>
            {history.length === 0 ? (
              <div style={{ textAlign: "center", color: "#999", padding: 40, fontSize: 14 }}>
                No experiments saved yet.
              </div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "2px solid #eee" }}>
                    {["Input", "Winner", "Tokens A/B", "Latency A/B", "Cost A/B", "Date"].map(h => (
                      <th key={h} style={{ padding: "8px 12px", textAlign: "left", color: "#666", fontWeight: 500 }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {history.map(row => (
                    <tr key={row.id} style={{ borderBottom: "1px solid #f0f0f0" }}>
                      <td style={{ padding: "10px 12px", color: "#333", maxWidth: 200 }}>{row.input}</td>
                      <td style={{ padding: "10px 12px" }}>
                        <span style={{
                          fontWeight: 700, fontSize: 15,
                          color: "#1D9E75"
                        }}>{row.winner}</span>
                      </td>
                      <td style={{ padding: "10px 12px", color: "#555" }}>{row.tokens_a} / {row.tokens_b}</td>
                      <td style={{ padding: "10px 12px", color: "#555" }}>{row.latency_a}ms / {row.latency_b}ms</td>
                      <td style={{ padding: "10px 12px", color: "#555" }}>${row.cost_a} / ${row.cost_b}</td>
                      <td style={{ padding: "10px 12px", color: "#999" }}>
                        {new Date(row.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </>
  )
}
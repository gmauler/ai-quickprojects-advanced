import { useState, useRef, useEffect } from "react"

const API = "http://localhost:8002"

const SYSTEM_PROMPTS = {
  "Assistant": "You are a helpful assistant.",
  "Security Expert": "You are a senior cybersecurity expert specialising in threat protection and incident response. Give precise, technical answers.",
  "PM Coach": "You are an experienced Product Manager coach at a major tech company. Help with product strategy, stakeholder management, and roadmap decisions.",
  "KQL Expert": "You are a KQL (Kusto Query Language) expert. Help write, optimise, and explain KQL queries for Azure Data Explorer and Microsoft Sentinel."
}

function Message({ role, content, streaming }) {
  const isUser = role === "user"
  return (
    <div style={{
      display: "flex",
      justifyContent: isUser ? "flex-end" : "flex-start",
      marginBottom: 16
    }}>
      <div style={{
        maxWidth: "72%",
        padding: "10px 14px",
        borderRadius: isUser ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
        background: isUser ? "#1a1a1a" : "#f4f4f4",
        color: isUser ? "#fff" : "#111",
        fontSize: 14,
        lineHeight: 1.6,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word"
      }}>
        {content}
        {streaming && (
          <span style={{
            display: "inline-block",
            width: 8, height: 14,
            background: "#666",
            marginLeft: 2,
            animation: "blink 1s step-end infinite",
            verticalAlign: "text-bottom"
          }} />
        )}
      </div>
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [streaming, setStreaming] = useState(false)
  const [selectedPersona, setSelectedPersona] = useState("Assistant")
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function send() {
    if (!input.trim() || streaming) return

    const userMessage = { role: "user", content: input.trim() }
    const newMessages = [...messages, userMessage]

    setMessages(newMessages)
    setInput("")
    setStreaming(true)

    // Add empty assistant message that will be filled by the stream
    setMessages(prev => [...prev, { role: "assistant", content: "" }])

    try {
      const response = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: newMessages,
          system: SYSTEM_PROMPTS[selectedPersona]
        })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let accumulated = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split("\n")

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6) // remove "data: " prefix

            if (data === "[DONE]") break

            // Restore newlines that were escaped for SSE
            const text = data.replace(/\\n/g, "\n")
            accumulated += text

            // Update the last message (assistant) with accumulated text
            setMessages(prev => {
              const updated = [...prev]
              updated[updated.length - 1] = {
                role: "assistant",
                content: accumulated
              }
              return updated
            })
          }
        }
      }
    } catch (e) {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: "assistant",
          content: "Error contacting the server."
        }
        return updated
      })
    }

    setStreaming(false)
    inputRef.current?.focus()
  }

  function clearChat() {
    setMessages([])
    inputRef.current?.focus()
  }

  return (
    <>
      <style>{`
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, sans-serif; background: #fff; }
        @keyframes blink { 0%, 100% { opacity: 1 } 50% { opacity: 0 } }
      `}</style>

      <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>

        {/* Header */}
        <div style={{
          padding: "14px 20px",
          borderBottom: "1px solid #eee",
          display: "flex",
          alignItems: "center",
          gap: 12
        }}>
          <span style={{ fontWeight: 600, fontSize: 16 }}>Claude Chat</span>
          <select
            value={selectedPersona}
            onChange={e => setSelectedPersona(e.target.value)}
            style={{
              padding: "4px 10px", borderRadius: 8,
              border: "1px solid #ddd", fontSize: 13,
              background: "#f9f9f9", cursor: "pointer"
            }}
          >
            {Object.keys(SYSTEM_PROMPTS).map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <button
            onClick={clearChat}
            style={{
              marginLeft: "auto", padding: "4px 12px",
              borderRadius: 8, border: "1px solid #ddd",
              fontSize: 13, cursor: "pointer", background: "transparent"
            }}
          >
            Clear
          </button>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
          {messages.length === 0 && (
            <div style={{
              textAlign: "center", color: "#999", marginTop: 80, fontSize: 14
            }}>
              Select a persona and start chatting
            </div>
          )}
          {messages.map((msg, i) => (
            <Message
              key={i}
              role={msg.role}
              content={msg.content}
              streaming={streaming && i === messages.length - 1 && msg.role === "assistant"}
            />
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div style={{
          padding: "14px 20px",
          borderTop: "1px solid #eee",
          display: "flex",
          gap: 10
        }}>
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()}
            placeholder={`Message ${selectedPersona}...`}
            disabled={streaming}
            style={{
              flex: 1, padding: "10px 14px",
              borderRadius: 10, border: "1px solid #ddd",
              fontSize: 14, outline: "none",
              background: streaming ? "#f9f9f9" : "#fff"
            }}
          />
          <button
            onClick={send}
            disabled={streaming || !input.trim()}
            style={{
              padding: "10px 20px",
              background: streaming ? "#999" : "#1a1a1a",
              color: "#fff", border: "none",
              borderRadius: 10, fontSize: 14,
              cursor: streaming ? "not-allowed" : "pointer"
            }}
          >
            {streaming ? "..." : "Send"}
          </button>
        </div>
      </div>
    </>
  )
}
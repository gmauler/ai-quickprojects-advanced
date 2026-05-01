import { useState, useEffect, useCallback } from "react"
import { useDropzone } from "react-dropzone"

const API = "http://localhost:8003"

function Badge({ status }) {
  const colors = {
    ready: { bg: "#E1F5EE", text: "#085041" },
    processing: { bg: "#FAEEDA", text: "#633806" },
    error: { bg: "#FCEBEB", text: "#501313" }
  }
  const c = colors[status] || colors.processing
  return (
    <span style={{
      fontSize: 11, fontWeight: 500, padding: "2px 8px",
      borderRadius: 20, background: c.bg, color: c.text
    }}>
      {status}
    </span>
  )
}

function HighlightedText({ text, query }) {
  if (!query.trim()) return <span>{text}</span>
  const parts = text.split(new RegExp(`(${query})`, "gi"))
  return (
    <span>
      {parts.map((part, i) =>
        part.toLowerCase() === query.toLowerCase()
          ? <mark key={i} style={{ background: "#FFF3CD", borderRadius: 2 }}>{part}</mark>
          : part
      )}
    </span>
  )
}

function Dropzone({ onUpload, uploading }) {
  const onDrop = useCallback(files => {
    if (files.length > 0) onUpload(files[0])
  }, [onUpload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "text/plain": [".txt"], "text/markdown": [".md"] },
    maxFiles: 1,
    disabled: uploading
  })

  return (
    <div {...getRootProps()} style={{
      border: `2px dashed ${isDragActive ? "#1a1a1a" : "#ddd"}`,
      borderRadius: 12, padding: "32px 20px",
      textAlign: "center", cursor: uploading ? "not-allowed" : "pointer",
      background: isDragActive ? "#f9f9f9" : "transparent",
      transition: "all 0.2s"
    }}>
      <input {...getInputProps()} />
      <div style={{ fontSize: 28, marginBottom: 8 }}>📄</div>
      <div style={{ fontSize: 14, color: "#555" }}>
        {uploading ? "Processing..." :
         isDragActive ? "Drop it here" :
         "Drag a PDF, TXT or MD file, or click to browse"}
      </div>
      <div style={{ fontSize: 12, color: "#999", marginTop: 4 }}>
        Max 10MB
      </div>
    </div>
  )
}

export default function App() {
  const [documents, setDocuments] = useState([])
  const [uploading, setUploading] = useState(false)
  const [query, setQuery] = useState("")
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState(null)
  const [tab, setTab] = useState("documents") // "documents" | "search"

  async function loadDocuments() {
    try {
      const res = await fetch(`${API}/documents`)
      setDocuments(await res.json())
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    loadDocuments()
    const interval = setInterval(loadDocuments, 3000)
    return () => clearInterval(interval)
  }, [])

  async function handleUpload(file) {
    setUploading(true)
    const form = new FormData()
    form.append("file", file)
    try {
      await fetch(`${API}/upload`, { method: "POST", body: form })
      await loadDocuments()
    } catch (e) {
      console.error(e)
    }
    setUploading(false)
  }

  async function handleSearch() {
    if (!query.trim()) return
    setSearching(true)
    try {
      const res = await fetch(`${API}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, limit: 5 })
      })
      setResults(await res.json())
    } catch (e) {
      console.error(e)
    }
    setSearching(false)
  }

  async function handleDelete(docId) {
    await fetch(`${API}/documents/${docId}`, { method: "DELETE" })
    setSelectedDoc(null)
    loadDocuments()
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

      <div style={{ maxWidth: 900, margin: "0 auto", padding: 24 }}>

        <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>
          Document Search
        </h1>
        <p style={{ fontSize: 14, color: "#666", marginBottom: 24 }}>
          Upload documents and search them semantically
        </p>

        {/* Tabs */}
        <div style={{ borderBottom: "1px solid #eee", marginBottom: 24, display: "flex", gap: 4 }}>
          <button style={tabStyle("documents")} onClick={() => setTab("documents")}>
            Documents ({documents.length})
          </button>
          <button style={tabStyle("search")} onClick={() => setTab("search")}>
            Search
          </button>
        </div>

        {tab === "documents" && (
          <div>
            <div style={{ marginBottom: 24 }}>
              <Dropzone onUpload={handleUpload} uploading={uploading} />
            </div>

            {documents.length === 0 ? (
              <div style={{ textAlign: "center", color: "#999", padding: 40, fontSize: 14 }}>
                No documents yet. Upload one above.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {documents.map(doc => (
                  <div
                    key={doc.id}
                    onClick={() => setSelectedDoc(selectedDoc?.id === doc.id ? null : doc)}
                    style={{
                      background: "#fff", border: `1px solid ${selectedDoc?.id === doc.id ? "#1a1a1a" : "#eee"}`,
                      borderRadius: 10, padding: "14px 16px", cursor: "pointer",
                      transition: "border-color 0.15s"
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                      <span style={{ fontWeight: 500, fontSize: 14, flex: 1 }}>{doc.filename}</span>
                      <Badge status={doc.status} />
                      <span style={{ fontSize: 12, color: "#999" }}>{doc.chunks} chunks</span>
                    </div>

                    {selectedDoc?.id === doc.id && doc.summary && (
                      <div style={{ marginTop: 10 }}>
                        <div style={{ fontSize: 12, color: "#666", marginBottom: 6 }}>Summary:</div>
                        <div style={{
                          fontSize: 13, color: "#333", lineHeight: 1.6,
                          background: "#f9f9f9", padding: 10, borderRadius: 8,
                          whiteSpace: "pre-wrap"
                        }}>
                          {doc.summary}
                        </div>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDelete(doc.id) }}
                          style={{
                            marginTop: 10, padding: "4px 12px", fontSize: 12,
                            border: "1px solid #ffcccc", borderRadius: 6,
                            background: "#fff5f5", color: "#cc0000", cursor: "pointer"
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "search" && (
          <div>
            <div style={{ display: "flex", gap: 10, marginBottom: 24 }}>
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSearch()}
                placeholder="Search across all documents..."
                style={{
                  flex: 1, padding: "10px 14px", borderRadius: 10,
                  border: "1px solid #ddd", fontSize: 14, outline: "none"
                }}
              />
              <button
                onClick={handleSearch}
                disabled={searching || !query.trim()}
                style={{
                  padding: "10px 20px", background: "#1a1a1a", color: "#fff",
                  border: "none", borderRadius: 10, fontSize: 14,
                  cursor: searching ? "not-allowed" : "pointer"
                }}
              >
                {searching ? "..." : "Search"}
              </button>
            </div>

            {results.length === 0 && query && !searching && (
              <div style={{ textAlign: "center", color: "#999", padding: 40, fontSize: 14 }}>
                No results found above similarity threshold.
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {results.map((r, i) => (
                <div key={i} style={{
                  background: "#fff", border: "1px solid #eee",
                  borderRadius: 10, padding: "14px 16px"
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 500, color: "#1a1a1a" }}>
                      {r.filename}
                    </span>
                    <span style={{ fontSize: 11, color: "#999" }}>chunk {r.chunk_index}</span>
                    <span style={{
                      marginLeft: "auto", fontSize: 11, fontWeight: 500,
                      color: r.similarity > 0.5 ? "#085041" : "#633806",
                      background: r.similarity > 0.5 ? "#E1F5EE" : "#FAEEDA",
                      padding: "2px 8px", borderRadius: 20
                    }}>
                      {(r.similarity * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <div style={{ fontSize: 13, color: "#333", lineHeight: 1.6 }}>
                    <HighlightedText text={r.content} query={query} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
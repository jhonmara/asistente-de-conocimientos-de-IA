import React, { useState, useEffect } from 'react'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000')

export default function App(){
  const [history, setHistory] = useState([{role:'system', content:'Eres útil y conciso.'}])
  const [msg, setMsg] = useState('')
  const [useRag, setUseRag] = useState(true)
  const [useWiki, setUseWiki] = useState(true)
  const [uploadStatus, setUploadStatus] = useState('')
  const [notes, setNotes] = useState([])

  const add = (role, content) => setHistory(h => [...h, {role, content}])

  useEffect(() => {
    fetch(`${API}/notes`).then(r=>r.json()).then(setNotes).catch(()=>{})
  }, [])

  async function send(){
    if(!msg.trim()) return
    add('user', msg)
    setMsg('')
    const payload = { messages: history.concat({role:'user', content: msg}), use_rag: useRag, use_wiki: useWiki }
    const res = await fetch(`${API}/chat`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) })
    const data = await res.json()
    add('assistant', data.answer || '(sin respuesta)')
  }

  async function uploadFile(e){
    const f = e.target.files?.[0]
    if(!f) return
    const fd = new FormData()
    fd.append('file', f)
    setUploadStatus('Subiendo...')
    const res = await fetch(`${API}/upload`, { method:'POST', body: fd })
    const data = await res.json()
    setUploadStatus(`Indexado: ${data.chunks_indexed} fragmentos`)
  }

  async function saveNote(){
    const title = prompt('Título de la nota')
    const body = prompt('Contenido de la nota')
    if(!title || !body) return
    const res = await fetch(`${API}/tools/note`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({title, body}) })
    const n = await res.json()
    setNotes(ns => [{id:n.id, title:n.title, created_at: new Date().toISOString()}, ...ns])
  }

  return (
    <div style={{maxWidth:900, margin:'0 auto', padding:24, fontFamily:'Inter, system-ui, Arial'}}>
      <h1>Mini RAG Assistant Pro</h1>
      <div style={{display:'flex', gap:8, alignItems:'center', marginBottom:12}}>
        <label><input type="checkbox" checked={useRag} onChange={e=>setUseRag(e.target.checked)}/> RAG</label>
        <label><input type="checkbox" checked={useWiki} onChange={e=>setUseWiki(e.target.checked)}/> Wikipedia</label>
        <input type="file" onChange={uploadFile} />
        <button onClick={saveNote}>Nueva nota</button>
        <span>{uploadStatus}</span>
      </div>
      <div style={{display:'grid', gridTemplateColumns:'2fr 1fr', gap:16}}>
        <div style={{border:'1px solid #ddd', borderRadius:12, padding:12}}>
          <div style={{minHeight:320}}>
            {history.map((t,i)=>(
              <div key={i} style={{marginBottom:8}}>
                <b>{t.role}:</b> <span>{t.content}</span>
              </div>
            ))}
          </div>
          <div style={{display:'flex', gap:8}}>
            <input style={{flex:1, padding:8}} value={msg} onChange={e=>setMsg(e.target.value)} placeholder="Escribe tu mensaje..." onKeyDown={(e)=>{if(e.key==='Enter') send()}} />
            <button onClick={send}>Enviar</button>
          </div>
        </div>
        <div>
          <h3>Notas recientes</h3>
          <ul>
            {notes.map(n=>(<li key={n.id}>{n.title} <small>({n.created_at})</small></li>))}
          </ul>
        </div>
      </div>
    </div>
  )
}

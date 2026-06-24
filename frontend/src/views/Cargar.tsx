import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, wsUrl } from "../api";
import { encolarCargas, pendientes, sincronizar } from "../offline";

export default function Cargar() {
  const nav = useNavigate();
  const [files, setFiles] = useState<File[]>([]);
  const [nivel, setNivel] = useState("RESERVADO");
  const [titulo, setTitulo] = useState("Briefing operacional " + new Date().toLocaleDateString("es-CL"));
  const [online, setOnline] = useState(navigator.onLine);
  const [cola, setCola] = useState(0);
  const [log, setLog] = useState<string[]>([]);
  const [generando, setGenerando] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    pendientes().then(setCola);
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);

  function push(m: string) {
    setLog((l) => [...l, m]);
    setTimeout(() => logRef.current?.scrollTo(0, 1e9), 0);
  }

  async function subir() {
    if (!files.length) return;
    if (online) {
      const r = await api.upload(files, nivel);
      push(`Subidos ${r.fuentes.length} documentos.`);
    } else {
      await encolarCargas(files, nivel);
      push(`Sin conexión: ${files.length} documentos en cola.`);
    }
    setFiles([]);
    setCola(await pendientes());
  }

  async function sync() {
    const n = await sincronizar();
    push(`Sincronizados ${n} documentos de la cola.`);
    setCola(await pendientes());
  }

  async function generar() {
    setGenerando(true);
    setLog([]);
    try {
      const r = await api.createBriefing(titulo);
      push(`Generación encolada (${r.fuentes} fuentes). Procesando…`);
      const ws = new WebSocket(wsUrl(r.task_id));
      ws.onmessage = (ev) => {
        const d = JSON.parse(ev.data);
        push(`· ${d.etapa}${d.doc_nombre ? " — " + d.doc_nombre : ""}${d.error ? " — " + d.error : ""}`);
        if (d.etapa === "completado") {
          push("✅ Briefing listo.");
          ws.close();
          setGenerando(false);
          setTimeout(() => nav(`/briefings/${r.briefing_id}`), 800);
        }
        if (d.etapa === "error") {
          push("❌ Falló la generación.");
          ws.close();
          setGenerando(false);
        }
      };
      ws.onerror = () => push("(WS sin conexión; el briefing igual se está generando)");
    } catch (e: any) {
      push("Error: " + e.message);
      setGenerando(false);
    }
  }

  return (
    <div>
      <div className="card">
        <h2>Cargar documentos {!online && <span className="offline">OFFLINE</span>}</h2>
        <p>Formatos: PDF, Word, Excel, correos (.msg/.eml), bitácoras (.txt).</p>
        <input type="file" multiple onChange={(e) => setFiles(Array.from(e.target.files || []))} />
        <label>Nivel de clasificación</label>
        <select value={nivel} onChange={(e) => setNivel(e.target.value)}>
          <option>PUBLICO</option><option>RESERVADO</option><option>SECRETO</option>
        </select>
        <button onClick={subir} disabled={!files.length}>
          {online ? "Subir" : "Encolar (offline)"}
        </button>{" "}
        {cola > 0 && <button className="sec" onClick={sync} disabled={!online}>Sincronizar cola ({cola})</button>}
      </div>

      <div className="card">
        <h2>Generar briefing</h2>
        <label>Título</label>
        <input value={titulo} onChange={(e) => setTitulo(e.target.value)} />
        <button onClick={generar} disabled={generando}>Cargar → Generar → Exportar</button>
        <div className="progress" ref={logRef} style={{ marginTop: 12 }}>
          {log.map((l, i) => <div key={i}>{l}</div>)}
        </div>
      </div>
    </div>
  );
}

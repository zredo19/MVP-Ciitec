import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";

function descargar(blob: Blob, nombre: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = nombre; a.click();
  URL.revokeObjectURL(url);
}

function Contenido({ c }: { c: any }) {
  if (!c) return <p>Sin contenido.</p>;
  return (
    <div>
      <h3>Resumen ejecutivo</h3>
      <ul className="bullets">
        {(c.resumen_ejecutivo || []).map((b: string, i: number) => <li key={i}>{b}</li>)}
      </ul>
      <h3>Situación</h3>
      <p>{c.situacion?.resumen || "-.-"}</p>
      {(c.situacion?.aspectos || []).length > 0 && (
        <ul className="bullets">
          {(c.situacion.aspectos || []).map((a: string, i: number) => <li key={i}>{a}</li>)}
        </ul>
      )}
      <h3>Asuntos críticos</h3>
      <table>
        <thead><tr><th>Asunto</th><th>Impacto</th><th>Responsable</th></tr></thead>
        <tbody>
          {(c.asuntos_criticos || []).map((a: any, i: number) => (
            <tr key={i}><td>{a.asunto || "-.-"}</td><td>{a.impacto || "-.-"}</td><td>{a.responsable || "-.-"}</td></tr>
          ))}
        </tbody>
      </table>
      <h3>Proyección 24–72h</h3>
      <p>{c.proyeccion_24_72h || "-.-"}</p>
      <details>
        <summary>Secciones institucionales (Personal · Inteligencia · Operaciones · Logística)</summary>
        <pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>
          {JSON.stringify({ personal: c.personal, inteligencia: c.inteligencia, operaciones: c.operaciones, logistica: c.logistica }, null, 2)}
        </pre>
      </details>
    </div>
  );
}

export default function Briefing() {
  const { id = "" } = useParams();
  const [b, setB] = useState<any>(null);
  const [versiones, setVersiones] = useState<any[]>([]);
  const [inc, setInc] = useState<any[]>([]);
  const [trazas, setTrazas] = useState<any[]>([]);
  const [at, setAt] = useState("");
  const [reconstruido, setReconstruido] = useState<any>(null);

  async function recargar() {
    setB(await api.getBriefing(id));
    setVersiones((await api.getVersiones(id)).versiones);
    setInc((await api.getInconsistencias(id)).inconsistencias);
    setTrazas((await api.getTrazabilidad(id)).trazas || []);
  }
  useEffect(() => { recargar(); }, [id]);

  async function exportar(formato: string) {
    const ext = formato === "PDF" ? "pdf" : formato === "WORD" ? "docx" : "txt";
    descargar(await api.exportar(id, formato), `${b.titulo}.${ext}`);
  }
  async function reconstruir() {
    if (!at) return;
    setReconstruido(await api.reconstruir(id, new Date(at).toISOString()));
  }

  if (!b) return <div className="card">Cargando…</div>;

  return (
    <div>
      <div className="card">
        <h2>{b.titulo} <span className={`badge ${b.nivel_clasificacion}`}>{b.nivel_clasificacion}</span></h2>
        <p>Estado: <b>{b.estado}</b> · Versión activa: {b.version ?? "—"}</p>
        <button onClick={() => exportar("PDF")}>Exportar PDF</button>{" "}
        <button onClick={() => exportar("WORD")}>Word</button>{" "}
        <button onClick={() => exportar("TEXTO")}>Texto</button>
      </div>

      <div className="card"><Contenido c={b.contenido} /></div>

      <div className="row">
        <div className="card">
          <h3>Inconsistencias (RF-005)</h3>
          {inc.length === 0 && <p>Sin inconsistencias.</p>}
          {inc.map((i) => (
            <p key={i.id}><span className={`badge ${i.tipo}`}>{i.tipo}</span> {i.descripcion}</p>
          ))}
        </div>
        <div className="card">
          <h3>Trazabilidad (RF-006)</h3>
          <p>{trazas.length} vínculos bullet → hecho → fuente.</p>
          <table><tbody>
            {trazas.slice(0, 12).map((t, i) => (
              <tr key={i}><td>{t.bullet_key}</td><td>{t.hecho_id.slice(0, 8)}…</td></tr>
            ))}
          </tbody></table>
        </div>
      </div>

      <div className="card">
        <h3>Versiones (RF-007) y reconstrucción a una hora (RF-009)</h3>
        <table>
          <thead><tr><th>Versión</th><th>Comentario</th><th>Aprobada</th><th>Creada</th><th></th></tr></thead>
          <tbody>
            {versiones.map((v) => (
              <tr key={v.id}>
                <td>v{v.numero_version}</td>
                <td>{v.comentario_cambio}</td>
                <td>{v.aprobado_en ? "Sí" : "No"}</td>
                <td>{v.creado_en?.slice(0, 16).replace("T", " ")}</td>
                <td>{!v.aprobado_en && <button onClick={() => api.aprobar(v.id).then(recargar)}>Aprobar</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ marginTop: 10 }}>
          <label>Reconstruir estado a la fecha/hora:</label>
          <div style={{ display: "flex", gap: 8 }}>
            <input type="datetime-local" value={at} onChange={(e) => setAt(e.target.value)} />
            <button onClick={reconstruir}>Reconstruir</button>
          </div>
          {reconstruido && (
            <div className="card" style={{ marginTop: 10, background: "#f8fafc" }}>
              <h4>Estado en {new Date(at).toLocaleString("es-CL")} — v{reconstruido.version}</h4>
              <Contenido c={reconstruido.contenido} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

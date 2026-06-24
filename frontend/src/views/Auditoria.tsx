import { useEffect, useState } from "react";
import { api } from "../api";

export default function Auditoria() {
  const [eventos, setEventos] = useState<any[]>([]);
  const [verif, setVerif] = useState<any>(null);

  useEffect(() => { api.getAudit().then((r) => setEventos(r.eventos)); }, []);

  return (
    <div>
      <div className="card">
        <h2>Audit log inmutable (RNF-003)</h2>
        <button onClick={() => api.verificarAudit().then(setVerif)}>Verificar cadena de hash</button>
        {verif && (
          <p style={{ color: verif.valido ? "#2e7d32" : "#c62828" }}>
            {verif.valido ? "✅ Cadena íntegra (tamper-evident)" : `❌ Cadena alterada en fila ${verif.integridad?.fila_rota}`}
          </p>
        )}
      </div>
      <div className="card">
        <table>
          <thead><tr><th>#</th><th>Acción</th><th>Entidad</th><th>Nivel</th><th>Cuándo</th><th>Hash</th></tr></thead>
          <tbody>
            {eventos.map((e) => (
              <tr key={e.id}>
                <td>{e.id}</td>
                <td>{e.accion}</td>
                <td>{e.entidad_tipo} {e.entidad_id?.slice(0, 8)}</td>
                <td>{e.nivel_afectado || "—"}</td>
                <td>{e.ocurrido_en?.slice(0, 19).replace("T", " ")}</td>
                <td title={e.hash_actual}>{e.hash_actual?.slice(0, 10)}…</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Icon } from "../components/icons";
import { Badge, fmtFecha } from "../components/ui";

const ROLES_AUDITORIA = ["Auditor", "Oficial de Seguridad", "Administrador del Sistema"];

export default function Auditoria() {
  const { user } = useAuth();
  const [eventos, setEventos] = useState<any[]>([]);
  const [verif, setVerif] = useState<any>(null);
  const [verificando, setVerificando] = useState(false);
  const [fAccion, setFAccion] = useState("");
  const [q, setQ] = useState("");

  const habilitado = user?.roles?.some((r) => ROLES_AUDITORIA.includes(r));

  useEffect(() => {
    if (habilitado) api.getAudit().then((r) => setEventos(r.eventos || []));
  }, [habilitado]);

  const acciones = useMemo(
    () => [...new Set(eventos.map((e) => e.accion))].sort(),
    [eventos]
  );
  const filtrados = useMemo(
    () =>
      eventos.filter(
        (e) =>
          (!fAccion || e.accion === fAccion) &&
          (!q ||
            `${e.accion} ${e.entidad_tipo} ${e.entidad_id}`.toLowerCase().includes(q.toLowerCase()))
      ),
    [eventos, fAccion, q]
  );

  async function verificar() {
    setVerificando(true);
    try {
      setVerif(await api.verificarAudit());
    } finally {
      setVerificando(false);
    }
  }

  if (!habilitado) {
    return (
      <div className="page">
        <div className="card">
          <div className="empty">
            <div className="empty__ico">
              <Icon name="lock" strokeWidth={1.6} />
            </div>
            <div className="empty__title">Acceso restringido</div>
            <p style={{ maxWidth: "46ch", margin: "0 auto" }}>
              El módulo de Auditoría está disponible solo para <strong>Auditor</strong>, Oficial de
              Seguridad y <strong>Administrador del Sistema</strong>. Su rol actual no tiene
              habilitación.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const filaRota = verif && !verif.valido ? verif.integridad?.fila_rota : null;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Registro inmutable · tamper-evident</div>
          <h1 className="page-title">Auditoría</h1>
          <p className="page-sub">
            Bitácora forense encadenada por hash. Cada evento referencia el hash del anterior.
          </p>
        </div>
        <button className="btn btn--primary" onClick={verificar} disabled={verificando}>
          {verificando ? (
            <>
              <span className="spin" /> Verificando…
            </>
          ) : (
            <>
              <Icon name="shield-check" />
              Verificar cadena de hash
            </>
          )}
        </button>
      </div>

      {verif && (
        <div
          className={"alert " + (verif.valido ? "alert--ok" : "alert--err")}
          style={{ marginBottom: "var(--sp-5)" }}
        >
          <Icon name={verif.valido ? "check-circle" : "alert-circle"} />
          {verif.valido ? (
            <span>
              <strong>✅ Cadena íntegra (tamper-evident).</strong> Los {eventos.length} eventos
              verifican correctamente.
            </span>
          ) : (
            <span>
              <strong>❌ Cadena alterada en la fila {filaRota ?? "?"}.</strong> El hash registrado no
              coincide con el recálculo — escalar a Seguridad.
            </span>
          )}
        </div>
      )}

      <div className="toolbar">
        <div className="search" style={{ flex: 1, minWidth: 240, maxWidth: 360 }}>
          <Icon name="search" />
          <input
            className="input"
            placeholder="Buscar por acción o entidad…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <select
          className="select"
          style={{ width: "auto" }}
          value={fAccion}
          onChange={(e) => setFAccion(e.target.value)}
        >
          <option value="">Todas las acciones</option>
          {acciones.map((a) => (
            <option key={a}>{a}</option>
          ))}
        </select>
        <div className="grow" />
        <span className="hint mono">{filtrados.length} eventos</span>
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th style={{ width: 48 }} className="num">
                #
              </th>
              <th>Acción</th>
              <th>Entidad</th>
              <th>Nivel</th>
              <th>Cuándo</th>
              <th>Hash</th>
            </tr>
          </thead>
          <tbody>
            {filtrados.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  Sin eventos registrados.
                </td>
              </tr>
            )}
            {filtrados.map((e) => {
              const rota = filaRota != null && String(filaRota) === String(e.id);
              const hash = e.hash_actual || "";
              return (
                <tr key={e.id} style={rota ? { background: "var(--sec-bg)" } : undefined}>
                  <td className="num mono">{String(e.id).slice(0, 6)}</td>
                  <td>
                    <span className="cell-mono" style={{ color: "var(--accent)", fontWeight: 600 }}>
                      {e.accion}
                    </span>
                  </td>
                  <td>
                    {e.entidad_tipo}{" "}
                    <span className="cell-sub mono">{e.entidad_id?.slice(0, 8)}</span>
                  </td>
                  <td>{e.nivel_afectado ? <Badge nivel={e.nivel_afectado} /> : <span className="muted">—</span>}</td>
                  <td className="cell-sub mono">{fmtFecha(e.ocurrido_en)?.replace(" ", " · ")}</td>
                  <td>
                    <span
                      className="tip mono"
                      style={{
                        fontSize: "var(--tx-sm)",
                        ...(rota ? { color: "var(--danger)", fontWeight: 600 } : {}),
                      }}
                    >
                      {hash.slice(0, 8)}…{hash.slice(-4)}
                      {rota ? " ⚠" : ""}
                      <span className="tip__pop">{hash}</span>
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

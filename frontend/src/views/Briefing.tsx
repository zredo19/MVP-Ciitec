import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Icon } from "../components/icons";
import { Badge, Pill, Tag, fmtFecha } from "../components/ui";

const ROLES_APROBACION = ["Comandante", "Administrador del Sistema"];
const SECCIONES: { key: string; titulo: string; icon: string }[] = [
  { key: "personal", titulo: "Personal", icon: "personal" },
  { key: "inteligencia", titulo: "Inteligencia", icon: "inteligencia" },
  { key: "operaciones", titulo: "Operaciones", icon: "operaciones" },
  { key: "logistica", titulo: "Logística", icon: "logistica" },
];

function descargar(blob: Blob, nombre: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nombre;
  a.click();
  URL.revokeObjectURL(url);
}

function esVacio(v: any): boolean {
  if (v == null) return true;
  if (typeof v === "string") return v.trim() === "" || v.trim() === "-.-";
  if (Array.isArray(v)) return v.length === 0;
  if (typeof v === "object") return Object.keys(v).length === 0;
  return false;
}
function esPrimitivo(v: any): boolean {
  return v == null || ["string", "number", "boolean"].includes(typeof v);
}
function humaniza(k: string): string {
  const s = k.replace(/_/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}
function valor(v: any): string {
  if (typeof v === "boolean") return v ? "Sí" : "No";
  return String(v);
}
function impactoStyle(imp?: string): React.CSSProperties {
  const s = (imp || "").toLowerCase();
  if (s.includes("alto")) return { color: "var(--sec)", background: "var(--sec-bg)" };
  if (s.includes("medio")) return { color: "var(--res)", background: "var(--res-bg)" };
  if (s.includes("bajo")) return { color: "var(--pub)", background: "var(--pub-bg)" };
  return { color: "var(--st-borrador)", background: "var(--st-borrador-bg)" };
}

// Renderiza una sección institucional (dict libre del LLM) de forma genérica:
// primitivas como métricas de tablero, listas/objetos como sub-bloques.
function SeccionInstitucional({
  titulo,
  icon,
  data,
  defaultOpen,
}: {
  titulo: string;
  icon: string;
  data: any;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(!!defaultOpen);
  const entries: [string, any][] = data && typeof data === "object" ? Object.entries(data) : [];
  const prim = entries.filter(([, v]) => esPrimitivo(v) || esVacio(v));
  const comp = entries.filter(([, v]) => !esPrimitivo(v) && !esVacio(v));

  return (
    <div className={"collapse" + (open ? " is-open" : "")}>
      <div className="collapse__head" onClick={() => setOpen((o) => !o)}>
        <div className="collapse__title">
          <Icon name={icon} />
          {titulo}
        </div>
        <Icon name="chevron" className="collapse__chev" />
      </div>
      <div className="collapse__body">
        {entries.length === 0 && <p className="muted">-.-</p>}
        {prim.length > 0 && (
          <div className="metrics">
            {prim.map(([k, v]) => {
              const vacio = esVacio(v);
              return (
                <div className="metric" key={k}>
                  <div className="metric__k">{humaniza(k)}</div>
                  <div className={"metric__v" + (vacio ? " is-empty" : "")}>
                    {vacio ? "-.-" : valor(v)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {comp.map(([k, v]) => (
          <div key={k} className="mt4">
            <div className="eyebrow">{humaniza(k)}</div>
            {Array.isArray(v) ? (
              <ul className="bullets mt2">
                {v.map((item, i) => (
                  <li key={i}>
                    {esPrimitivo(item)
                      ? valor(item)
                      : Object.values(item)
                          .filter((x) => esPrimitivo(x) && !esVacio(x))
                          .map(valor)
                          .join(" · ")}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="metrics mt2">
                {Object.entries(v).map(([sk, sv]) => (
                  <div className="metric" key={sk}>
                    <div className="metric__k">{humaniza(sk)}</div>
                    <div className={"metric__v" + (esVacio(sv) ? " is-empty" : "")}>
                      {esVacio(sv) ? "-.-" : esPrimitivo(sv) ? valor(sv) : JSON.stringify(sv)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Briefing() {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const [b, setB] = useState<any>(null);
  const [versiones, setVersiones] = useState<any[]>([]);
  const [inc, setInc] = useState<any[]>([]);
  const [trazas, setTrazas] = useState<any[]>([]);
  const [at, setAt] = useState("");
  const [reconstruido, setReconstruido] = useState<any>(null);
  const [lit, setLit] = useState<string | null>(null);
  const [diff, setDiff] = useState<string[] | null>(null);
  const [verDiff, setVerDiff] = useState(false);

  const puedeAprobar = user?.roles?.some((r) => ROLES_APROBACION.includes(r));

  async function recargar() {
    const [det, vs, ins, trz] = await Promise.all([
      api.getBriefing(id),
      api.getVersiones(id),
      api.getInconsistencias(id),
      api.getTrazabilidad(id),
    ]);
    setB(det);
    setVersiones(vs.versiones || []);
    setInc(ins.inconsistencias || []);
    setTrazas(trz.trazas || []);
  }
  useEffect(() => {
    recargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function exportar(formato: string) {
    const ext = formato === "PDF" ? "pdf" : formato === "WORD" ? "docx" : "txt";
    descargar(await api.exportar(id, formato), `${b.titulo}.${ext}`);
  }
  async function reconstruir() {
    if (!at) return;
    setReconstruido(await api.reconstruir(id, new Date(at).toISOString()));
  }
  async function aprobar(versionId: string) {
    await api.aprobar(versionId);
    await recargar();
  }
  async function toggleDiff() {
    if (verDiff) {
      setVerDiff(false);
      return;
    }
    if (versiones.length >= 2) {
      const a = versiones[versiones.length - 2].numero_version;
      const bb = versiones[versiones.length - 1].numero_version;
      try {
        const r = await api.getDiff(id, a, bb);
        setDiff(r.diff || []);
      } catch {
        setDiff([]);
      }
    }
    setVerDiff(true);
  }

  if (!b) return <div className="page">Cargando…</div>;

  const c = b.contenido;
  // Correlación bullet ↔ traza: las bullet_key únicas, en orden, mapean a los
  // bullets del resumen ejecutivo (RF-006).
  const bulletKeys: string[] = [...new Set(trazas.map((t: any) => t.bullet_key))] as string[];
  const grupos = bulletKeys.map((k) => ({
    key: k,
    hechos: trazas.filter((t: any) => t.bullet_key === k).map((t: any) => t.hecho_id),
  }));
  const resumen: string[] = c?.resumen_ejecutivo || [];
  const aspectos: string[] = c?.situacion?.aspectos || [];
  const asuntos: any[] = c?.asuntos_criticos || [];

  const ultimaDiff =
    versiones.length >= 2
      ? `v${versiones[versiones.length - 2].numero_version}→v${versiones[versiones.length - 1].numero_version}`
      : "";

  return (
    <div className="page">
      <div className="row gap2" style={{ marginBottom: "var(--sp-4)" }}>
        <Link className="btn btn--ghost btn--sm" to="/briefings">
          <Icon name="arrow-left" />
          Briefings
        </Link>
        <span className="muted">/</span>
        <span className="muted mono" style={{ fontSize: "var(--tx-sm)" }}>
          {id.slice(0, 8)}
        </span>
      </div>

      <div className="page-head">
        <div>
          <div className="row gap2 row--wrap" style={{ marginBottom: 8 }}>
            <Badge nivel={b.nivel_clasificacion} lg />
            <Pill estado={b.estado} />
            <span className="muted" style={{ fontSize: "var(--tx-sm)" }}>
              Versión activa <strong className="mono">{b.version != null ? `v${b.version}` : "—"}</strong>
            </span>
          </div>
          <h1 className="page-title">{b.titulo}</h1>
          <p className="page-sub">Generado el {fmtFecha(b.creado_en)}</p>
        </div>
        <div className="btn-group">
          <button className="btn btn--secondary" onClick={() => exportar("PDF")}>
            <Icon name="file-text" />
            PDF
          </button>
          <button className="btn btn--secondary" onClick={() => exportar("WORD")}>
            <Icon name="file" />
            Word
          </button>
          <button className="btn btn--secondary" onClick={() => exportar("TEXTO")}>
            <Icon name="text-lines" />
            Texto
          </button>
        </div>
      </div>

      {!c ? (
        <div className="card">
          <div className="card__body muted">
            El briefing aún no tiene una versión con contenido (estado {b.estado}).
          </div>
        </div>
      ) : (
        <div className="detail-grid">
          {/* ---- columna principal ---- */}
          <div className="stack">
            <div className="card">
              <div className="card__head">
                <div className="card__title">
                  <Icon name="clipboard" className="card__icon" />
                  Resumen ejecutivo
                </div>
                <span className="hint mono">
                  {trazas.length} vínculos bullet → hecho → fuente
                </span>
              </div>
              <div className="card__body">
                {resumen.length === 0 ? (
                  <p className="muted">-.-</p>
                ) : (
                  <ul className="bullets">
                    {resumen.map((t, i) => {
                      const key = bulletKeys[i];
                      const hecho = grupos[i]?.hechos?.[0];
                      return (
                        <li key={i}>
                          <div
                            className={"trace-bullet" + (key && lit === key ? " is-lit" : "")}
                            onMouseEnter={() => key && setLit(key)}
                            onMouseLeave={() => setLit(null)}
                          >
                            <span>{t}</span>
                            {hecho && (
                              <span className="trace-id mono">{String(hecho).slice(0, 8)}</span>
                            )}
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>

            <div className="card">
              <div className="card__head">
                <div className="card__title">Situación</div>
              </div>
              <div className="card__body">
                <p style={{ fontSize: "var(--tx-md)", lineHeight: 1.6, marginBottom: "var(--sp-4)" }}>
                  {c.situacion?.resumen || "-.-"}
                </p>
                {aspectos.length > 0 && (
                  <>
                    <div className="eyebrow">Aspectos relevantes</div>
                    <ul className="bullets">
                      {aspectos.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </div>

            <div className="card">
              <div className="card__head">
                <div className="card__title">
                  <Icon name="alert-triangle" className="card__icon" style={{ color: "var(--res)" }} />
                  Asuntos críticos
                </div>
              </div>
              <div className="table-wrap" style={{ border: 0, borderRadius: 0 }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th style={{ width: "42%" }}>Asunto</th>
                      <th>Impacto</th>
                      <th>Responsable</th>
                    </tr>
                  </thead>
                  <tbody>
                    {asuntos.length === 0 && (
                      <tr>
                        <td colSpan={3} className="muted">
                          -.-
                        </td>
                      </tr>
                    )}
                    {asuntos.map((a, i) => (
                      <tr key={i}>
                        <td className="cell-strong">{a.asunto || "-.-"}</td>
                        <td>
                          <span className="pill" style={impactoStyle(a.impacto)}>
                            <span className="pill__dot" />
                            {a.impacto || "-.-"}
                          </span>
                        </td>
                        <td>{a.responsable || "-.-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="card__head">
                <div className="card__title">
                  <Icon name="trending" className="card__icon" />
                  Proyección 24–72 h
                </div>
              </div>
              <div className="card__body">
                <p style={{ fontSize: "var(--tx-md)", lineHeight: 1.6 }}>
                  {c.proyeccion_24_72h || "-.-"}
                </p>
              </div>
            </div>

            <div>
              <div className="eyebrow" style={{ marginBottom: "var(--sp-3)" }}>
                Secciones institucionales
              </div>
              {SECCIONES.map((s, i) => (
                <SeccionInstitucional
                  key={s.key}
                  titulo={s.titulo}
                  icon={s.icon}
                  data={c[s.key]}
                  defaultOpen={i === 0}
                />
              ))}
            </div>

            <div className="card">
              <div className="card__head">
                <div className="card__title">
                  <Icon name="alert-circle" className="card__icon" style={{ color: "var(--inc-con)" }} />
                  Inconsistencias detectadas
                </div>
                <span className="hint">{inc.length}</span>
              </div>
              <div className="card__body">
                {inc.length === 0 ? (
                  <p className="muted">Sin inconsistencias.</p>
                ) : (
                  inc.map((i) => (
                    <div className="inc-item" key={i.id}>
                      <div>
                        <Tag tipo={i.tipo} />
                      </div>
                      <div className="inc-item__body">
                        <div className="inc-item__desc">{i.descripcion}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* ---- columna lateral ---- */}
          <div className="stack">
            <div className="card trace-panel">
              <div className="card__head">
                <div className="card__title">
                  <Icon name="link" className="card__icon" />
                  Trazabilidad
                </div>
              </div>
              <div className="card__body">
                <p className="hint" style={{ marginBottom: "var(--sp-3)" }}>
                  Pase el cursor por un bullet del resumen para resaltar su hecho y documento origen.
                </p>
                {grupos.length === 0 ? (
                  <p className="muted">Sin vínculos de trazabilidad.</p>
                ) : (
                  <div className="stack" style={{ gap: 8 }}>
                    {grupos.map((g) => (
                      <div
                        key={g.key}
                        className={"trace-link" + (lit === g.key ? " is-lit" : "")}
                        onMouseEnter={() => setLit(g.key)}
                        onMouseLeave={() => setLit(null)}
                      >
                        <div className="trace-link__h">
                          <span className="badge badge--res" style={{ height: 18 }}>
                            {String(g.key).toUpperCase()}
                          </span>
                          Vínculo de trazabilidad
                        </div>
                        <div className="trace-link__hecho">
                          {g.hechos.length} hecho{g.hechos.length === 1 ? "" : "s"} ·{" "}
                          <span className="mono" style={{ color: "var(--accent)" }}>
                            {String(g.hechos[0] || "").slice(0, 8)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="card">
              <div className="card__head">
                <div className="card__title">Versiones</div>
                {versiones.length >= 2 && (
                  <button className="btn btn--ghost btn--sm" onClick={toggleDiff}>
                    {verDiff ? "Ocultar diff" : `Ver diff ${ultimaDiff}`}
                  </button>
                )}
              </div>
              <div className="card__body">
                <div className="stack" style={{ gap: "var(--sp-4)" }}>
                  {versiones.map((v) => (
                    <div className="ver-row" key={v.id}>
                      <span className={"ver-dot" + (v.aprobado_en ? " is-appr" : "")} />
                      <div className="grow">
                        <div className="row row--between gap2">
                          <span className="cell-strong mono">v{v.numero_version}</span>
                          {v.aprobado_en ? (
                            <span className="pill pill--aprobado">
                              <span className="pill__dot" />
                              Aprobada
                            </span>
                          ) : puedeAprobar ? (
                            <button
                              className="btn btn--primary btn--sm"
                              onClick={() => aprobar(v.id)}
                            >
                              Aprobar
                            </button>
                          ) : (
                            <span className="hint">Sin aprobar</span>
                          )}
                        </div>
                        {v.comentario_cambio && (
                          <div className="cell-sub" style={{ marginTop: 3 }}>
                            {v.comentario_cambio}
                          </div>
                        )}
                        <div className="cell-sub mono" style={{ marginTop: 2, fontSize: 11 }}>
                          {v.aprobado_en ? "Aprobada " + fmtFecha(v.aprobado_en) : "Creada " + fmtFecha(v.creado_en)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {verDiff && (
                  <div className="mt4">
                    {!diff || diff.length === 0 ? (
                      <p className="hint">Sin diferencias para mostrar.</p>
                    ) : (
                      <div className="diff">
                        {diff.map((ln, i) => {
                          const add = ln.startsWith("+") && !ln.startsWith("+++");
                          const del = ln.startsWith("-") && !ln.startsWith("---");
                          const cls = add ? "diff__line--add" : del ? "diff__line--del" : "diff__line--ctx";
                          const sign = add ? "+" : del ? "−" : "~";
                          return (
                            <div className={"diff__line " + cls} key={i}>
                              <span className="diff__sign">{sign}</span>
                              {ln.replace(/^[+\- ]/, "")}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="card">
              <div className="card__head">
                <div className="card__title">
                  <Icon name="clock" className="card__icon" />
                  Reconstrucción point-in-time
                </div>
              </div>
              <div className="card__body">
                <label className="label" style={{ marginBottom: 6, display: "block" }}>
                  Estado del briefing a una fecha/hora
                </label>
                <input
                  className="input"
                  type="datetime-local"
                  value={at}
                  onChange={(e) => setAt(e.target.value)}
                />
                <button className="btn btn--secondary btn--block mt2" onClick={reconstruir} disabled={!at}>
                  Reconstruir estado
                </button>
                {reconstruido && (
                  <div className="pit-result">
                    <Icon name="clock" style={{ color: "var(--accent)" }} />
                    <div>
                      <div style={{ fontWeight: 600 }}>
                        Estado del briefing a esa hora — v{reconstruido.version}
                      </div>
                      <div className="hint">
                        Versión vigente el {new Date(at).toLocaleString("es-CL")}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

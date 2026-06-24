import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Briefings() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { api.listBriefings().then((r) => setItems(r.briefings)); }, []);

  return (
    <div className="card">
      <h2>Briefings</h2>
      <table>
        <thead><tr><th>Título</th><th>Versión</th><th>Estado</th><th>Clasificación</th><th>Creado</th></tr></thead>
        <tbody>
          {items.map((b) => (
            <tr key={b.id}>
              <td><Link to={`/briefings/${b.id}`}>{b.titulo}</Link></td>
              <td>{b.version_activa ?? "—"}</td>
              <td>{b.estado}</td>
              <td><span className={`badge ${b.nivel_clasificacion}`}>{b.nivel_clasificacion}</span></td>
              <td>{b.creado_en?.slice(0, 16).replace("T", " ")}</td>
            </tr>
          ))}
          {!items.length && <tr><td colSpan={5}>Aún no hay briefings.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

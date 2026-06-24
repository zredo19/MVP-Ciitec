import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import Login from "./views/Login";
import Cargar from "./views/Cargar";
import Briefings from "./views/Briefings";
import Briefing from "./views/Briefing";
import Auditoria from "./views/Auditoria";

function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const esAuditor = user?.roles.some((r) => ["Auditor", "Oficial de Seguridad", "Administrador del Sistema"].includes(r));
  return (
    <div>
      <header className="topbar">
        <span className="brand">★ Síntesis de Briefings — CIITEC</span>
        <nav>
          <Link to="/cargar">Cargar</Link>
          <Link to="/briefings">Briefings</Link>
          {esAuditor && <Link to="/auditoria">Auditoría</Link>}
        </nav>
        <span className="user">
          {user?.nombre} · {user?.nivel_habilitacion}{" "}
          <button onClick={logout}>Salir</button>
        </span>
      </header>
      <main className="container">{children}</main>
    </div>
  );
}

function Protected({ children }: { children: React.ReactNode }) {
  const { user, cargando } = useAuth();
  const loc = useLocation();
  if (cargando) return <div className="container">Cargando…</div>;
  if (!user) return <Navigate to="/login" state={{ from: loc }} replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/cargar" element={<Protected><Cargar /></Protected>} />
      <Route path="/briefings" element={<Protected><Briefings /></Protected>} />
      <Route path="/briefings/:id" element={<Protected><Briefing /></Protected>} />
      <Route path="/auditoria" element={<Protected><Auditoria /></Protected>} />
      <Route path="*" element={<Navigate to="/cargar" replace />} />
    </Routes>
  );
}

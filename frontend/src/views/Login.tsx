import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [u, setU] = useState("operaciones");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  const [cargando, setCargando] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(""); setCargando(true);
    try {
      await login(u, p);
      nav("/cargar");
    } catch {
      setErr("Credenciales inválidas");
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="container">
      <form className="card login-box" onSubmit={submit}>
        <h2>★ Acceso institucional</h2>
        <label>Usuario</label>
        <input value={u} onChange={(e) => setU(e.target.value)} autoFocus />
        <label>Contraseña</label>
        <input type="password" value={p} onChange={(e) => setP(e.target.value)} />
        {err && <p style={{ color: "#c62828" }}>{err}</p>}
        <button disabled={cargando}>{cargando ? "Validando…" : "Ingresar"}</button>
      </form>
    </div>
  );
}

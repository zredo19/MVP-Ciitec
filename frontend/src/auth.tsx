import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api, getToken, setToken } from "./api";

type Usuario = {
  id: string; username: string; nombre: string;
  unidad?: string; nivel_habilitacion: string; roles: string[];
};

type AuthCtx = {
  user: Usuario | null;
  cargando: boolean;
  login: (u: string, p: string) => Promise<void>;
  logout: () => void;
};

const Ctx = createContext<AuthCtx>(null as any);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    if (!getToken()) { setCargando(false); return; }
    api.me().then(setUser).catch(() => setToken(null)).finally(() => setCargando(false));
  }, []);

  async function login(u: string, p: string) {
    const r = await api.login(u, p);
    setToken(r.token);
    setUser(r.usuario);
  }
  function logout() {
    setToken(null);
    setUser(null);
    location.href = "/login";
  }

  return <Ctx.Provider value={{ user, cargando, login, logout }}>{children}</Ctx.Provider>;
}

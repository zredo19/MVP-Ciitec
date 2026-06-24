// Tema claro/oscuro. El oscuro está pensado para sala de operaciones.
// Se persiste en localStorage y se refleja en data-theme del <html>.
import { useEffect, useState } from "react";

const KEY = "tema";
type Tema = "light" | "dark";

function inicial(): Tema {
  const guardado = localStorage.getItem(KEY) as Tema | null;
  if (guardado === "light" || guardado === "dark") return guardado;
  return "light";
}

export function useTheme() {
  const [tema, setTema] = useState<Tema>(inicial);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", tema);
    localStorage.setItem(KEY, tema);
  }, [tema]);

  const alternar = () => setTema((t) => (t === "dark" ? "light" : "dark"));
  return { tema, alternar };
}

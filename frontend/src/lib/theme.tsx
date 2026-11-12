import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

export type Tema = "claro" | "escuro" | "sistema";
const KEY = "shiplog-tema";

const Ctx = createContext<{ tema: Tema; setTema: (t: Tema) => void; escuro: boolean; alternar: () => void } | null>(null);

function ler(): Tema {
  try {
    return (localStorage.getItem(KEY) as Tema) || "sistema";
  } catch {
    return "sistema";
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [tema, setTemaState] = useState<Tema>(ler);
  const [sistemaEscuro, setSistemaEscuro] = useState(() => matchMedia("(prefers-color-scheme: dark)").matches);

  useEffect(() => {
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const fn = (e: MediaQueryListEvent) => setSistemaEscuro(e.matches);
    mq.addEventListener("change", fn);
    return () => mq.removeEventListener("change", fn);
  }, []);

  const escuro = tema === "escuro" || (tema === "sistema" && sistemaEscuro);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", escuro);
  }, [escuro]);

  const setTema = useCallback((t: Tema) => {
    setTemaState(t);
    try {
      localStorage.setItem(KEY, t);
    } catch {
      /* armazenamento indisponível */
    }
  }, []);
  const alternar = useCallback(() => setTema(escuro ? "claro" : "escuro"), [escuro, setTema]);

  return <Ctx.Provider value={{ tema, setTema, escuro, alternar }}>{children}</Ctx.Provider>;
}

export function useTheme() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useTheme fora do ThemeProvider");
  return c;
}

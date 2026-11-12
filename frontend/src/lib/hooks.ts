import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type { Job } from "./types";

/** Polling dos jobs ativos: 1s enquanto houver algum, 10s caso contrário (spec 005 §3.4). */
export function useJobsAtivos() {
  const qc = useQueryClient();
  const anteriores = useRef<Map<number, Job>>(new Map());
  const q = useQuery({
    queryKey: ["jobs", "ativos"],
    queryFn: api.jobsAtivos,
    refetchInterval: (query) => ((query.state.data?.length ?? 0) > 0 ? 1000 : 10000),
  });

  useEffect(() => {
    const atuais = new Map((q.data ?? []).map((j) => [j.id, j]));
    const terminaram = [...anteriores.current.keys()].filter((id) => !atuais.has(id));
    if (terminaram.length) {
      for (const id of terminaram) {
        const j = anteriores.current.get(id)!;
        qc.invalidateQueries({ queryKey: ["job", id] });
        qc.invalidateQueries({ queryKey: ["project", j.projeto_id] });
        qc.invalidateQueries({ queryKey: [j.tipo === "post" ? "posts" : "articles", j.projeto_id] });
        qc.invalidateQueries({ queryKey: ["geracoes", j.projeto_id] });
      }
      qc.invalidateQueries({ queryKey: ["projects"] });
    }
    anteriores.current = atuais;
  }, [q.data, qc]);

  return q;
}

export function useHealth() {
  return useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 60_000, staleTime: 30_000 });
}

/** Alvo global do atalho "copiar texto atual" (RUI-15). */
let copyTarget: (() => void) | null = null;
export function useCopyTarget(fn: (() => void) | null) {
  useEffect(() => {
    copyTarget = fn;
    return () => {
      if (copyTarget === fn) copyTarget = null;
    };
  }, [fn]);
}
export function runCopyTarget(): boolean {
  if (copyTarget) {
    copyTarget();
    return true;
  }
  return false;
}

export function useHotkey(combo: (e: KeyboardEvent) => boolean, handler: (e: KeyboardEvent) => void) {
  const ref = useRef(handler);
  ref.current = handler;
  useEffect(() => {
    const fn = (e: KeyboardEvent) => {
      if (combo(e)) ref.current(e);
    };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

export const mod = (e: KeyboardEvent) => e.metaKey || e.ctrlKey;
export function emCampoDeTexto(e: KeyboardEvent) {
  const t = e.target as HTMLElement | null;
  return !!t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable || t.tagName === "SELECT");
}

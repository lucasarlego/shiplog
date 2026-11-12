import { useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, FileSearch, GitBranch, PenLine, RotateCcw, Square, Clock, Bug } from "lucide-react";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";
import type { Job, StatusJob } from "@/lib/types";
import { cn } from "@/lib/utils";
import { dur, ease } from "@/lib/motion";
import { duracao } from "@/lib/format";
import { Button } from "./ui/button";
import { Dialog } from "./ui/dialog";

const ETAPAS: { key: StatusJob; label: string; icon: typeof Clock }[] = [
  { key: "na_fila", label: "Na fila", icon: Clock },
  { key: "clonando", label: "Clonando", icon: GitBranch },
  { key: "analisando", label: "Analisando", icon: FileSearch },
  { key: "gerando", label: "Escrevendo", icon: PenLine },
  { key: "concluido", label: "Pronto", icon: Check },
];
// Post sem repositório (spec 006): não há clone nem análise.
const ETAPAS_LIVRE = ETAPAS.filter((e) => e.key !== "clonando" && e.key !== "analisando");

/** Stepper animado de progresso (RUI-09). A etapa ativa é a única animação em loop. */
export function JobStepper({ job, compact = false, livre = false }: { job: Job; compact?: boolean; livre?: boolean }) {
  const reduce = useReducedMotion();
  const qc = useQueryClient();
  const etapas = livre ? ETAPAS_LIVRE : ETAPAS;
  const idx = etapas.findIndex((e) => e.key === job.status);
  const cancelar = useMutation({
    mutationFn: () => api.cancelar(job.id),
    onSuccess: () => {
      toast("Geração cancelada");
      qc.invalidateQueries({ queryKey: ["jobs", "ativos"] });
    },
    onError: (e: ApiError) => toast.error(e.message),
  });

  if (compact) {
    const etapa = etapas[Math.max(idx, 0)];
    return (
      <div className="flex items-center gap-2 text-xs text-fg-muted" role="status" aria-live="polite">
        <span className="relative flex size-2">
          <motion.span
            className="absolute inline-flex size-full rounded-full bg-grad-primary"
            animate={reduce ? { opacity: [0.5, 1, 0.5] } : { scale: [1, 1.8, 1], opacity: [0.7, 0, 0.7] }}
            transition={{ duration: dur.pulse, repeat: Infinity, ease: ease.inOut }}
          />
          <span className="relative inline-flex size-2 rounded-full bg-primary" />
        </span>
        {etapa.label}
        {job.status === "na_fila" && job.posicao_fila > 1 ? ` · ${job.posicao_fila}º na fila` : "…"}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-grad p-4 shadow-md border" role="status" aria-live="polite">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-sm font-medium">
          Gerando {job.tipo === "post" ? "post" : "artigo"}
          {job.status === "na_fila" && job.posicao_fila > 1 && (
            <span className="ml-2 text-fg-subtle">· {job.posicao_fila}º na fila</span>
          )}
        </div>
        <Button size="sm" variant="ghost" onClick={() => cancelar.mutate()} loading={cancelar.isPending}>
          <Square /> Cancelar
        </Button>
      </div>
      <ol className="flex items-center">
        {etapas.map((e, i) => {
          const feito = i < idx;
          const ativo = i === idx;
          const Icon = feito ? Check : e.icon;
          return (
            <li key={e.key} className={cn("flex items-center", i < etapas.length - 1 && "flex-1")}>
              <div className="flex flex-col items-center gap-1.5">
                <div className="relative">
                  {ativo && (
                    <motion.span
                      className="absolute -inset-1 rounded-full bg-grad-primary"
                      animate={reduce ? { opacity: [0.25, 0.6, 0.25] } : { opacity: [0.35, 0.8, 0.35], scale: [1, 1.12, 1] }}
                      transition={{ duration: dur.pulse, repeat: Infinity, ease: ease.inOut }}
                    />
                  )}
                  <div
                    className={cn(
                      "relative flex size-8 items-center justify-center rounded-full border transition-colors duration-base",
                      feito && "border-transparent bg-primary text-primary-fg",
                      ativo && "border-transparent bg-surface text-primary",
                      !feito && !ativo && "border-border bg-surface-2 text-fg-subtle",
                    )}
                  >
                    <Icon className="size-4" />
                  </div>
                </div>
                <span className={cn("text-xs", ativo ? "font-medium text-fg" : "text-fg-subtle")}>{e.label}</span>
              </div>
              {i < etapas.length - 1 && (
                <div className="relative mx-2 mb-5 h-0.5 flex-1 overflow-hidden rounded-full bg-surface-3">
                  <motion.div
                    className="absolute inset-y-0 left-0 bg-grad-primary"
                    initial={false}
                    animate={{ width: feito ? "100%" : "0%" }}
                    transition={{ duration: dur.slower, ease: ease.out }}
                  />
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/** Card de erro com mensagem, ação sugerida, retry e detalhes (Tratamento de erros, RI-06). */
export function JobError({ job, onRetried }: { job: Job; onRetried?: (j: Job) => void }) {
  const qc = useQueryClient();
  const [debugOpen, setDebugOpen] = useState(false);
  const retry = useMutation({
    mutationFn: () => api.retry(job.id),
    onSuccess: (j) => {
      qc.invalidateQueries({ queryKey: ["jobs", "ativos"] });
      onRetried?.(j);
    },
    onError: (e: ApiError) => toast.error(e.message, { description: e.erro.acao_sugerida ?? undefined }),
  });
  const cancelado = job.status === "cancelado";
  return (
    <div
      className={cn(
        "rounded-lg border p-4",
        cancelado ? "border-border bg-surface-2" : "border-st-erro/30 bg-st-erro-soft",
      )}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className={cn("mt-0.5 size-5 shrink-0", cancelado ? "text-fg-subtle" : "text-st-erro")} />
        <div className="min-w-0 flex-1">
          <div className="font-medium">{cancelado ? "Geração cancelada" : "A geração falhou"}</div>
          {!cancelado && <p className="mt-1 text-sm text-fg-muted break-words">{job.erro}</p>}
          {job.acao_sugerida && !cancelado && <p className="mt-1 text-sm font-medium">{job.acao_sugerida}</p>}
          <div className="mt-3 flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => retry.mutate()} loading={retry.isPending}>
              <RotateCcw /> Tentar novamente
            </Button>
            {!cancelado && (
              <Button size="sm" variant="ghost" onClick={() => setDebugOpen(true)}>
                <Bug /> Ver detalhes
              </Button>
            )}
          </div>
        </div>
      </div>
      <DebugDialog id={job.id} open={debugOpen} onOpenChange={setDebugOpen} />
    </div>
  );
}

export function DebugDialog({ id, open, onOpenChange }: { id: number; open: boolean; onOpenChange: (o: boolean) => void }) {
  const q = useQuery({ queryKey: ["debug", id], queryFn: () => api.debug(id), enabled: open });
  const [aba, setAba] = useState<"resposta" | "prompt">("resposta");
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Detalhes da geração" className="w-[min(94vw,900px)]"
      description={q.data ? `Status ${q.data.status} · ${q.data.tentativas} tentativa(s) · código de saída ${q.data.codigo_saida ?? "—"} · ${duracao(q.data.duracao_ms)}` : "Carregando…"}>
      <div className="mb-2 flex gap-1">
        {(["resposta", "prompt"] as const).map((a) => (
          <Button key={a} size="sm" variant={aba === a ? "soft" : "ghost"} onClick={() => setAba(a)}>
            {a === "resposta" ? "Resposta bruta" : "Prompt enviado"}
          </Button>
        ))}
      </div>
      <pre className="max-h-[60vh] overflow-auto rounded-md border border-border bg-surface-2 p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap break-words">
        {(aba === "resposta" ? q.data?.resposta_bruta : q.data?.prompt) || "(vazio)"}
      </pre>
    </Dialog>
  );
}

export function AvisosJob({ avisos }: { avisos: string[] }) {
  if (!avisos?.length) return null;
  const textos: Record<string, string> = {
    analise_parcial: "Repositório grande: a coleta de metadados foi parcial.",
    repo_alterado: "O Claude tentou alterar arquivos do clone; as alterações foram desfeitas.",
    correcao_aplicada: "A resposta precisou de uma correção automática de formato.",
  };
  return (
    <div className="flex flex-col gap-1">
      {avisos.map((a) => (
        <div key={a} className="flex items-center gap-2 text-xs text-st-novos">
          <AlertTriangle className="size-3.5" /> {textos[a] ?? a}
        </div>
      ))}
    </div>
  );
}

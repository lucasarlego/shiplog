import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileText, Sparkles, Upload, UserRound, X } from "lucide-react";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";
import type { Config } from "@/lib/types";
import { cn } from "@/lib/utils";
import { relativo } from "@/lib/format";
import { Button } from "./ui/button";
import { Textarea } from "./ui/input";
import { Card } from "./ui/misc";

const ACEITOS = [".pdf", ".docx", ".txt", ".md"];
const MAX_BYTES = 5 * 1024 * 1024;

function paraBase64(f: File): Promise<string> {
  return new Promise((ok, falha) => {
    const r = new FileReader();
    r.onload = () => ok(String(r.result).split(",", 2)[1] ?? "");
    r.onerror = () => falha(r.error);
    r.readAsDataURL(f);
  });
}

/** Perfil profissional: currículo + texto livre → Claude escreve o perfil usado em todos os prompts (spec 007). */
export function ProfileCard({ cfg }: { cfg: Config }) {
  const qc = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [arrastando, setArrastando] = useState(false);
  const [sobre, setSobre] = useState(cfg.perfil_sobre);
  const [perfil, setPerfil] = useState(cfg.perfil_profissional);
  const [salvo, setSalvo] = useState(true);
  const atualizar = (c: Config) => qc.setQueryData(["settings"], c);
  const erro = (e: ApiError) => toast.error(e.message, { description: e.erro?.acao_sugerida ?? undefined });

  useEffect(() => setPerfil(cfg.perfil_profissional), [cfg.perfil_profissional]);

  const enviar = useMutation({
    mutationFn: async (f: File) => api.enviarCurriculo(f.name, await paraBase64(f)),
    onSuccess: (c) => { atualizar(c); toast.success("Currículo enviado"); },
    onError: erro,
  });
  const remover = useMutation({ mutationFn: api.removerCurriculo, onSuccess: atualizar, onError: erro });
  const gerar = useMutation({
    mutationFn: () => api.gerarPerfil(sobre),
    onSuccess: (c) => { atualizar(c); setSalvo(true); toast.success("Perfil profissional gerado", { description: "Revise e ajuste o texto se quiser." }); },
    onError: erro,
  });
  const salvarPerfil = useMutation({
    mutationFn: (v: string) => api.salvarConfig({ perfil_profissional: v }),
    onSuccess: (c) => { atualizar(c); setSalvo(true); },
    onError: erro,
  });

  // Autosave do perfil editado à mão.
  useEffect(() => {
    if (perfil === cfg.perfil_profissional) return;
    const t = setTimeout(() => salvarPerfil.mutate(perfil), 800);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [perfil]);

  const escolher = (f: File | undefined) => {
    if (!f) return;
    const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
    if (!ACEITOS.includes(ext)) return toast.error("Envie o currículo em PDF, DOCX, TXT ou MD.");
    if (f.size > MAX_BYTES) return toast.error("O currículo passou de 5 MB.");
    enviar.mutate(f);
  };

  const temMaterial = !!cfg.curriculo_nome || sobre.trim().length >= 20;

  return (
    <Card className="flex flex-col gap-5 p-5">
      <div className="flex items-start gap-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary-soft-fg">
          <UserRound className="size-4.5" />
        </div>
        <div>
          <h2 className="font-semibold">Perfil profissional</h2>
          <p className="text-sm text-fg-muted">
            Envie seu currículo e conte o que ele não diz. O Claude monta um perfil que entra em todos os posts e artigos,
            para o texto soar como alguém com a sua trajetória.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Currículo</span>
          {cfg.curriculo_nome ? (
            <div className="flex min-h-[132px] flex-col justify-between rounded-lg border border-border bg-surface-2 p-3">
              <div className="flex items-center gap-2.5">
                <FileText className="size-5 shrink-0 text-accent" />
                <span className="min-w-0 flex-1 truncate text-sm font-medium" title={cfg.curriculo_nome}>{cfg.curriculo_nome}</span>
                <Button size="icon-sm" variant="ghost" aria-label="Remover currículo" onClick={() => remover.mutate()} loading={remover.isPending}>
                  <X />
                </Button>
              </div>
              <Button size="sm" variant="outline" className="self-start" onClick={() => input.current?.click()} loading={enviar.isPending}>
                <Upload /> Trocar arquivo
              </Button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => input.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setArrastando(true); }}
              onDragLeave={() => setArrastando(false)}
              onDrop={(e) => { e.preventDefault(); setArrastando(false); escolher(e.dataTransfer.files[0]); }}
              className={cn(
                "flex min-h-[132px] flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed border-border-strong p-4 text-center transition-colors duration-fast",
                "hover:border-primary hover:bg-primary-soft/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
                arrastando && "border-primary bg-primary-soft/40",
              )}
            >
              <Upload className={cn("size-5 text-fg-subtle", enviar.isPending && "animate-pulse")} />
              <span className="text-sm font-medium">{enviar.isPending ? "Enviando…" : "Arraste ou clique para enviar"}</span>
              <span className="text-xs text-fg-subtle">PDF, DOCX, TXT ou MD · até 5 MB · fica só na sua máquina</span>
            </button>
          )}
          <input ref={input} type="file" accept={ACEITOS.join(",")} className="hidden" onChange={(e) => { escolher(e.target.files?.[0]); e.target.value = ""; }} />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="perfil-sobre" className="text-sm font-medium">Sobre você <span className="font-normal text-fg-subtle">(opcional)</span></label>
          <Textarea
            id="perfil-sobre"
            value={sobre}
            onChange={(e) => setSobre(e.target.value)}
            maxLength={8000}
            className="min-h-[132px] flex-1 text-sm"
            placeholder="O que não está no currículo: cargo e foco atuais, projetos recentes, temas pelos quais quer ser lembrado, para quem você escreve…"
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="text-xs text-fg-subtle">
          {gerar.isPending
            ? cfg.curriculo_nome ? "O Claude está lendo o currículo… (até 1 minuto)" : "O Claude está escrevendo o perfil…"
            : cfg.perfil_gerado_em ? `Último perfil gerado ${relativo(cfg.perfil_gerado_em)}` : "Nenhum perfil gerado ainda."}
        </span>
        <Button variant="primary" onClick={() => gerar.mutate()} loading={gerar.isPending} disabled={!temMaterial}>
          <Sparkles /> {cfg.perfil_profissional ? "Gerar de novo" : "Gerar perfil com Claude"}
        </Button>
      </div>

      <AnimatePresence initial={false}>
        {(perfil || cfg.perfil_gerado_em) && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="flex flex-col gap-1.5 overflow-hidden">
            <div className="flex items-center justify-between">
              <label htmlFor="perfil-texto" className="text-sm font-medium">Perfil usado nas gerações</label>
              <span className="text-xs text-fg-subtle" aria-live="polite">{salvarPerfil.isPending ? "Salvando…" : salvo ? "Salvo" : "Editando…"}</span>
            </div>
            <Textarea
              id="perfil-texto"
              value={perfil}
              onChange={(e) => { setPerfil(e.target.value); setSalvo(false); }}
              maxLength={6000}
              className="min-h-[220px] font-mono text-sm leading-relaxed"
            />
            <span className="text-xs text-fg-subtle">Você pode editar à vontade. Apague o texto para não usar perfil nas gerações.</span>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

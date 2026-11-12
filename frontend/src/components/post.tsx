import { useCallback, useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, CircleDot, Copy, Hash, Lightbulb, Save, Send, Undo2, X } from "lucide-react";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";
import type { Post } from "@/lib/types";
import { cn, copiar, modKey } from "@/lib/utils";
import { CORTE_VER_MAIS, LIMITE_LINKEDIN, textoCompletoPost } from "@/lib/format";
import { useCopyTarget } from "@/lib/hooks";
import { dur, ease } from "@/lib/motion";
import { Button } from "./ui/button";
import { Textarea } from "./ui/input";
import { Card, Tooltip } from "./ui/misc";
import { PublishDialog } from "./versions";

/** Contador de caracteres com limite do LinkedIn (RF-19). */
export function CharCounter({ total, inicio, linhaCorte }: { total: number; inicio: number; linhaCorte: number }) {
  const estado = total > LIMITE_LINKEDIN ? "erro" : total >= LIMITE_LINKEDIN * 0.9 ? "aviso" : "ok";
  const pct = Math.min(100, (total / LIMITE_LINKEDIN) * 100);
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs" aria-live="polite">
      <div className="h-1.5 w-28 overflow-hidden rounded-full bg-surface-3">
        <motion.div
          className={cn("h-full rounded-full", estado === "erro" ? "bg-st-erro" : estado === "aviso" ? "bg-st-novos" : "bg-primary")}
          animate={{ width: `${pct}%` }}
          transition={{ duration: dur.base, ease: ease.out }}
        />
      </div>
      <span className={cn("whitespace-nowrap font-mono tabular-nums", estado === "erro" ? "font-semibold text-st-erro" : estado === "aviso" ? "text-st-novos" : "text-fg-muted")}>
        {total.toLocaleString("pt-BR")} / {LIMITE_LINKEDIN.toLocaleString("pt-BR")}
      </span>
      {estado === "erro" && (
        <span className="inline-flex items-center gap-1 font-medium text-st-erro">
          <AlertTriangle className="size-3.5" /> Acima do limite do LinkedIn
        </span>
      )}
      <span className="text-fg-subtle">
        “Ver mais” corta na linha {linhaCorte} · abertura {Math.min(inicio, CORTE_VER_MAIS)}/{CORTE_VER_MAIS} caracteres
      </span>
    </div>
  );
}

/** Pré-visualização com quebras de linha como no LinkedIn e corte do "ver mais" (RF-19). */
export function LinkedInPreview({ texto, hashtags, revelar }: { texto: string; hashtags: string[]; revelar: boolean }) {
  const [expandido, setExpandido] = useState(false);
  const reduce = useReducedMotion();
  const corpo = textoCompletoPost(texto, hashtags);
  const cortado = corpo.length > CORTE_VER_MAIS && !expandido;
  const visivel = cortado ? corpo.slice(0, CORTE_VER_MAIS).trimEnd() : corpo;
  const linhas = visivel.split("\n");
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-2.5 border-b border-border px-4 py-3">
        <div className="size-9 rounded-full bg-grad-primary" aria-hidden />
        <div className="leading-tight">
          <div className="text-sm font-semibold">Você</div>
          <div className="text-xs text-fg-subtle">Pré-visualização · LinkedIn</div>
        </div>
      </div>
      <div className="px-4 py-3 text-md leading-relaxed whitespace-pre-wrap break-words">
        {linhas.map((l, i) => (
          <motion.span
            key={`${i}-${revelar}`}
            className="block min-h-[1.6em]"
            initial={revelar ? { opacity: 0, y: reduce ? 0 : 4 } : false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: dur.base, ease: ease.out, delay: revelar ? Math.min(i * 0.04, 0.7) : 0 }}
          >
            {renderHashtags(l)}
            {cortado && i === linhas.length - 1 && (
              <>
                {"… "}
                <button className="font-medium text-fg-subtle hover:text-primary hover:underline" onClick={() => setExpandido(true)}>
                  ver mais
                </button>
              </>
            )}
          </motion.span>
        ))}
        {expandido && corpo.length > CORTE_VER_MAIS && (
          <button className="mt-2 text-sm text-fg-subtle hover:underline" onClick={() => setExpandido(false)}>
            ver menos
          </button>
        )}
      </div>
    </Card>
  );
}

function renderHashtags(l: string) {
  const partes = l.split(/(#[\p{L}\p{N}_]+)/u);
  return partes.map((p, i) =>
    p.startsWith("#") ? (
      <span key={i} className="font-medium text-primary">{p}</span>
    ) : (
      <span key={i}>{p}</span>
    ),
  );
}

function primeiroParagrafo(t: string) {
  const i = t.indexOf("\n\n");
  return i === -1 ? t.length : i;
}

export function PostEditor({ post, novo }: { post: Post; novo: boolean }) {
  const qc = useQueryClient();
  const [texto, setTexto] = useState(post.texto);
  const [hashtags, setHashtags] = useState(post.hashtags);
  const [tagInput, setTagInput] = useState("");
  const [pubOpen, setPubOpen] = useState(false);
  useEffect(() => {
    setTexto(post.texto);
    setHashtags(post.hashtags);
  }, [post.id, post.texto, post.hashtags]);

  const sujo = texto !== post.texto || hashtags.join(" ") !== post.hashtags.join(" ");
  const completo = textoCompletoPost(texto, hashtags);
  const inicio = primeiroParagrafo(texto);
  const invalidar = () => {
    qc.invalidateQueries({ queryKey: ["posts", post.projeto_id] });
    qc.invalidateQueries({ queryKey: ["projects"] });
    qc.invalidateQueries({ queryKey: ["project", post.projeto_id] });
  };

  const salvar = useMutation({
    mutationFn: () => api.salvarPost(post.id, { texto, hashtags }),
    onSuccess: (p) => {
      toast.success(`Salvo como v${p.versao}`);
      qc.setQueryData<Post[]>(["posts", post.projeto_id], (old) => (old ? [p, ...old] : [p]));
      invalidar();
    },
    onError: (e: ApiError) => toast.error(e.message),
  });
  const status = useMutation({
    mutationFn: ({ s, link }: { s: string; link?: string }) => api.statusPost(post.id, s, link),
    onSuccess: () => invalidar(),
    onError: (e: ApiError) => toast.error(e.message, { description: e.erro.acao_sugerida ?? undefined }),
  });

  const copiarTexto = useCallback(async () => {
    if (await copiar(completo)) toast.success("Post copiado", { description: "Texto + hashtags na área de transferência." });
    else toast.error("Não foi possível copiar.");
  }, [completo]);
  useCopyTarget(copiarTexto);

  const usarGancho = (g: string) => {
    const resto = inicio < texto.length ? texto.slice(inicio) : "";
    setTexto(g.trim() + resto);
    toast("Abertura trocada", { description: "Salve para criar uma nova versão." });
  };

  const linhaCorte = useMemo(() => {
    const ate = texto.slice(0, CORTE_VER_MAIS);
    return ate.split("\n").length;
  }, [texto]);

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,400px)]">
      <div className="flex min-w-0 flex-col gap-4">
        <div>
          <Textarea
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            className="min-h-[340px] font-sans text-md"
            aria-label="Texto do post"
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && sujo) {
                e.preventDefault();
                salvar.mutate();
              }
            }}
          />
        </div>
        <CharCounter total={completo.length} inicio={inicio} linhaCorte={linhaCorte} />

        <div className="flex flex-wrap items-center gap-1.5">
          <Hash className="size-4 text-fg-subtle" />
          {hashtags.map((h) => (
            <span key={h} className="inline-flex items-center gap-1 rounded-full bg-primary-soft px-2.5 py-0.5 text-sm text-primary-soft-fg">
              {h}
              <button aria-label={`Remover ${h}`} onClick={() => setHashtags(hashtags.filter((x) => x !== h))} className="opacity-60 hover:opacity-100">
                <X className="size-3" />
              </button>
            </span>
          ))}
          <input
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => {
              if ((e.key === "Enter" || e.key === ",") && tagInput.trim()) {
                e.preventDefault();
                const t = tagInput.trim().replace(/\s+/g, "");
                const h = t.startsWith("#") ? t : `#${t}`;
                if (!hashtags.includes(h)) setHashtags([...hashtags, h]);
                setTagInput("");
              }
            }}
            placeholder="+ hashtag"
            aria-label="Adicionar hashtag"
            className="h-7 w-28 rounded-full border border-dashed border-border bg-transparent px-2.5 text-sm outline-none focus:border-primary"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-border pt-4">
          <Tooltip content={`${modKey()}+Shift+C`}>
            <Button variant="primary" onClick={copiarTexto}>
              <Copy /> Copiar post
            </Button>
          </Tooltip>
          {sujo && (
            <>
              <Tooltip content={`${modKey()}+Enter`}>
                <Button variant="soft" onClick={() => salvar.mutate()} loading={salvar.isPending}>
                  <Save /> Salvar como nova versão
                </Button>
              </Tooltip>
              <Button variant="ghost" onClick={() => { setTexto(post.texto); setHashtags(post.hashtags); }}>
                <Undo2 /> Descartar
              </Button>
            </>
          )}
          <div className="ml-auto flex gap-2">
            {post.status === "rascunho" && (
              <Button variant="outline" onClick={() => status.mutate({ s: "pronto" })} loading={status.isPending && status.variables?.s === "pronto"} disabled={sujo}>
                <CircleDot /> Marcar como pronto
              </Button>
            )}
            {post.status !== "publicado" ? (
              <Button variant="outline" onClick={() => setPubOpen(true)} disabled={sujo}>
                <Send /> Marcar como publicado
              </Button>
            ) : (
              <Button variant="ghost" onClick={() => status.mutate({ s: "pronto" })}>
                <Undo2 /> Desfazer publicação
              </Button>
            )}
          </div>
        </div>
        {post.status === "publicado" && (
          <div className="flex items-center gap-2 rounded-md bg-st-publicado-soft px-3 py-2 text-sm text-st-publicado">
            <Check className="size-4" /> Publicado {post.publicado_em && `em ${new Date(post.publicado_em).toLocaleDateString("pt-BR")}`}
            {post.link && (
              <a href={post.link} target="_blank" rel="noreferrer" className="ml-1 truncate underline underline-offset-2">
                {post.link}
              </a>
            )}
          </div>
        )}
      </div>

      <div className="flex min-w-0 flex-col gap-4">
        <LinkedInPreview texto={texto} hashtags={hashtags} revelar={novo} />
        {post.hooks_alternativos.length > 0 && (
          <Card className="p-4">
            <div className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-fg-subtle">
              <Lightbulb className="size-3.5" /> Ganchos alternativos
            </div>
            <div className="flex flex-col gap-2">
              {post.hooks_alternativos.map((g, i) => (
                <button
                  key={i}
                  onClick={() => usarGancho(g)}
                  className="rounded-md border border-border p-3 text-left text-sm leading-relaxed transition-[border-color,background-color] duration-fast hover:border-primary hover:bg-primary-soft/40"
                >
                  {g}
                  <span className="mt-1 block text-xs text-fg-subtle">Clique para usar como abertura</span>
                </button>
              ))}
            </div>
          </Card>
        )}
        <Card className="p-4 text-sm">
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-fg-subtle">Resumo técnico</div>
          <p className="text-fg-muted">{post.resumo_tecnico}</p>
          {post.destaques.length > 0 && (
            <>
              <div className="mb-1 mt-3 text-xs font-medium uppercase tracking-wide text-fg-subtle">Destaques do código</div>
              <ul className="list-disc space-y-1 pl-4 text-fg-muted">
                {post.destaques.map((d, i) => <li key={i}>{d}</li>)}
              </ul>
            </>
          )}
        </Card>
      </div>

      <PublishDialog
        key={`${post.id}-${pubOpen}`}
        open={pubOpen}
        onOpenChange={setPubOpen}
        plataforma="LinkedIn"
        linkInicial={post.link}
        loading={status.isPending}
        onConfirm={async (link) => {
          await status.mutateAsync({ s: "publicado", link });
        }}
      />
    </div>
  );
}

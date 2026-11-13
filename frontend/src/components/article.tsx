import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion, useReducedMotion } from "motion/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, CircleDot, Copy, Download, Eye, FileCode2, ImageIcon, PenLine, Save, Send, Undo2 } from "lucide-react";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";
import type { Artigo } from "@/lib/types";
import { baixar, copiar, cn } from "@/lib/utils";
import { useCopyTarget } from "@/lib/hooks";
import { dur, ease } from "@/lib/motion";
import { Button } from "./ui/button";
import { Input, Textarea } from "./ui/input";
import { Card, Field } from "./ui/misc";
import { ParametrosVersao, PublishDialog } from "./versions";

export function MarkdownPreview({ markdown, revelar }: { markdown: string; revelar?: boolean }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      key={revelar ? markdown.length : "static"}
      initial={revelar ? { opacity: 0, y: reduce ? 0 : 6 } : false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: dur.slower, ease: ease.out }}
      className="prose-md"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ a: (p) => <a {...p} target="_blank" rel="noreferrer" /> }}>
        {markdown}
      </ReactMarkdown>
    </motion.div>
  );
}

function markdownCompleto(a: { titulo: string; subtitulo: string; corpo_markdown: string }) {
  return `# ${a.titulo}\n\n${a.subtitulo ? `*${a.subtitulo}*\n\n` : ""}${a.corpo_markdown.trim()}\n`;
}

export function ArticleEditor({ artigo, novo }: { artigo: Artigo; novo: boolean }) {
  const qc = useQueryClient();
  const [titulo, setTitulo] = useState(artigo.titulo);
  const [subtitulo, setSubtitulo] = useState(artigo.subtitulo);
  const [corpo, setCorpo] = useState(artigo.corpo_markdown);
  const [tags, setTags] = useState(artigo.tags.join(", "));
  const [modo, setModo] = useState<"preview" | "editar">("preview");
  const [pubOpen, setPubOpen] = useState(false);
  useEffect(() => {
    setTitulo(artigo.titulo);
    setSubtitulo(artigo.subtitulo);
    setCorpo(artigo.corpo_markdown);
    setTags(artigo.tags.join(", "));
  }, [artigo.id, artigo.titulo, artigo.subtitulo, artigo.corpo_markdown, artigo.tags]);

  const listaTags = tags.split(",").map((t) => t.trim()).filter(Boolean);
  const sujo =
    titulo !== artigo.titulo || subtitulo !== artigo.subtitulo || corpo !== artigo.corpo_markdown || listaTags.join(",") !== artigo.tags.join(",");
  const invalidar = () => {
    qc.invalidateQueries({ queryKey: ["articles", artigo.projeto_id] });
    qc.invalidateQueries({ queryKey: ["projects"] });
    qc.invalidateQueries({ queryKey: ["project", artigo.projeto_id] });
  };
  const salvar = useMutation({
    mutationFn: () => api.salvarArtigo(artigo.id, { titulo, subtitulo, corpo_markdown: corpo, tags: listaTags.slice(0, 5) }),
    onSuccess: (a) => {
      toast.success(`Salvo como v${a.versao}`);
      qc.setQueryData<Artigo[]>(["articles", artigo.projeto_id], (old) => (old ? [a, ...old] : [a]));
      invalidar();
    },
    onError: (e: ApiError) => toast.error(e.message),
  });
  const status = useMutation({
    mutationFn: ({ s, link }: { s: string; link?: string }) => api.statusArtigo(artigo.id, s, link),
    onSuccess: invalidar,
    onError: (e: ApiError) => toast.error(e.message, { description: e.erro.acao_sugerida ?? undefined }),
  });
  const copiarMd = useCallback(async () => {
    if (await copiar(markdownCompleto({ titulo, subtitulo, corpo_markdown: corpo }))) toast.success("Markdown copiado");
    else toast.error("Não foi possível copiar.");
  }, [titulo, subtitulo, corpo]);
  useCopyTarget(copiarMd);

  const palavras = corpo.split(/\s+/).filter(Boolean).length;

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="flex min-w-0 flex-col gap-4">
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-md bg-surface-2 p-0.5">
            {(["preview", "editar"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setModo(m)}
                className={cn("flex h-7 items-center gap-1.5 rounded-sm px-3 text-sm text-fg-muted transition-colors duration-fast [&_svg]:size-3.5", modo === m && "bg-surface text-fg shadow-sm")}
                aria-pressed={modo === m}
              >
                {m === "preview" ? <Eye /> : <PenLine />} {m === "preview" ? "Pré-visualizar" : "Editar Markdown"}
              </button>
            ))}
          </div>
          <span className="ml-auto text-xs text-fg-subtle">{palavras.toLocaleString("pt-BR")} palavras · ~{Math.max(1, Math.round(palavras / 230))} min de leitura</span>
        </div>

        {modo === "editar" ? (
          <div className="flex flex-col gap-3">
            <Field label="Título" htmlFor="art-titulo"><Input id="art-titulo" value={titulo} onChange={(e) => setTitulo(e.target.value)} /></Field>
            <Field label="Subtítulo" htmlFor="art-sub"><Input id="art-sub" value={subtitulo} onChange={(e) => setSubtitulo(e.target.value)} /></Field>
            <Field label="Corpo (Markdown)" htmlFor="art-corpo">
              <Textarea id="art-corpo" value={corpo} onChange={(e) => setCorpo(e.target.value)} className="min-h-[520px] font-mono text-sm" />
            </Field>
            <Field label="Tags (até 5, separadas por vírgula)" htmlFor="art-tags">
              <Input id="art-tags" value={tags} onChange={(e) => setTags(e.target.value)} aria-invalid={listaTags.length > 5} />
            </Field>
          </div>
        ) : (
          <Card className="px-8 py-7">
            <h1 className="text-3xl font-semibold leading-tight tracking-tight">{titulo}</h1>
            {subtitulo && <p className="mt-2 text-lg text-fg-muted">{subtitulo}</p>}
            <div className="mt-6 border-t border-border pt-2">
              <MarkdownPreview markdown={corpo} revelar={novo} />
            </div>
          </Card>
        )}

        <div className="flex flex-wrap items-center gap-2 border-t border-border pt-4">
          <Button variant="primary" onClick={copiarMd}><Copy /> Copiar Markdown</Button>
          <Button variant="outline" onClick={() => baixar(api.exportArtigoUrl(artigo.id))} disabled={sujo}>
            <Download /> Exportar .md
          </Button>
          {sujo && (
            <>
              <Button variant="soft" onClick={() => salvar.mutate()} loading={salvar.isPending} disabled={listaTags.length > 5}>
                <Save /> Salvar como nova versão
              </Button>
              <Button variant="ghost" onClick={() => { setTitulo(artigo.titulo); setSubtitulo(artigo.subtitulo); setCorpo(artigo.corpo_markdown); setTags(artigo.tags.join(", ")); }}>
                <Undo2 /> Descartar
              </Button>
            </>
          )}
          <div className="ml-auto flex gap-2">
            {artigo.status === "rascunho" && (
              <Button variant="outline" onClick={() => status.mutate({ s: "pronto" })} disabled={sujo}><CircleDot /> Marcar como pronto</Button>
            )}
            {artigo.status !== "publicado" ? (
              <Button variant="outline" onClick={() => setPubOpen(true)} disabled={sujo}><Send /> Marcar como publicado</Button>
            ) : (
              <Button variant="ghost" onClick={() => status.mutate({ s: "pronto" })}><Undo2 /> Desfazer publicação</Button>
            )}
          </div>
        </div>
        {artigo.status === "publicado" && (
          <div className="flex items-center gap-2 rounded-md bg-st-publicado-soft px-3 py-2 text-sm text-st-publicado">
            <Check className="size-4" /> Publicado
            {artigo.link && <a href={artigo.link} target="_blank" rel="noreferrer" className="truncate underline underline-offset-2">{artigo.link}</a>}
          </div>
        )}
      </div>

      <div className="flex min-w-0 flex-col gap-4">
        <Card className="p-4">
          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-fg-subtle">Tags do Medium</div>
          <div className="flex flex-wrap gap-1.5">
            {artigo.tags.map((t) => <span key={t} className="rounded-full bg-accent-soft px-2.5 py-0.5 text-sm text-accent-soft-fg">{t}</span>)}
          </div>
        </Card>
        <Card className="p-4">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-fg-subtle">
            <FileCode2 className="size-3.5" /> Código real citado
          </div>
          <ul className="space-y-1.5">
            {artigo.trechos_de_codigo.map((t, i) => (
              <li key={i} className="flex items-center justify-between gap-2 rounded-sm bg-surface-2 px-2 py-1 font-mono text-xs">
                <span className="truncate">{t.arquivo}</span>
                <span className="shrink-0 text-fg-subtle">L{t.linhas}</span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-fg-subtle">Todos os caminhos foram verificados no repositório.</p>
        </Card>
        {artigo.sugestoes_de_imagens.length > 0 && (
          <Card className="p-4">
            <div className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-fg-subtle">
              <ImageIcon className="size-3.5" /> Sugestões de imagens
            </div>
            <ul className="list-disc space-y-1 pl-4 text-sm text-fg-muted">
              {artigo.sugestoes_de_imagens.map((s, i) => <li key={i}>{s}</li>)}
            </ul>
          </Card>
        )}
        <ParametrosVersao versao={artigo} />
      </div>

      <PublishDialog
        key={`${artigo.id}-${pubOpen}`}
        open={pubOpen}
        onOpenChange={setPubOpen}
        plataforma="Medium"
        linkInicial={artigo.link}
        loading={status.isPending}
        onConfirm={async (link) => {
          await status.mutateAsync({ s: "publicado", link });
        }}
      />
    </div>
  );
}

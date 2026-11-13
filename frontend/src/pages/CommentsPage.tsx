import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, CheckCheck, Copy, ExternalLink, ImagePlus, MessageSquareText, Plus, RefreshCw, Sparkles, Terminal, Trash2, Undo2, X } from "lucide-react";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";
import type { Comentario, PlataformaComentario } from "@/lib/types";
import { cn, copiar } from "@/lib/utils";
import { relativo } from "@/lib/format";
import { fadeUp } from "@/lib/motion";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Card, Field, Kbd, Skeleton } from "@/components/ui/misc";
import { Select, type Opcao } from "@/components/ui/select";

const OBJETIVOS: { value: string; label: string; desc: string }[] = [
  { value: "acrescentar", label: "Acrescentar", desc: "Somar um ponto de vista ou experiência" },
  { value: "apoiar", label: "Apoiar", desc: "Reconhecer de forma específica" },
  { value: "perguntar", label: "Perguntar", desc: "Puxar conversa com uma boa pergunta" },
  { value: "discordar", label: "Contrapor", desc: "Discordar com respeito" },
];
const OP_TAMANHO: Opcao[] = [
  { value: "curto", label: "Curto", desc: "1–3 frases" },
  { value: "medio", label: "Médio", desc: "3–5 frases" },
];
const OP_IDIOMA: Opcao[] = [
  { value: "auto", label: "Igual ao post" },
  { value: "pt", label: "Português" },
  { value: "en", label: "Inglês" },
];
const PLATAFORMAS: { value: PlataformaComentario; label: string }[] = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "medium", label: "Medium" },
];
const NOME_PLATAFORMA: Record<PlataformaComentario, string> = { linkedin: "LinkedIn", medium: "Medium" };

function Selos({ c }: { c: Comentario }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <span className="rounded-full bg-surface-2 px-2 py-0.5 text-xs text-fg-muted">{NOME_PLATAFORMA[c.plataforma] ?? c.plataforma}</span>
      {c.status === "usado" && <span className="inline-flex items-center gap-1 rounded-full bg-primary-soft px-2 py-0.5 text-xs text-primary-soft-fg"><CheckCheck className="size-3" /> Usado</span>}
      {c.fonte === "claude_code" && <span className="inline-flex items-center gap-1 rounded-full bg-surface-2 px-2 py-0.5 text-xs text-fg-muted"><Terminal className="size-3" /> via Claude Code</span>}
    </span>
  );
}

const EXT_OK = ["png", "jpg", "jpeg", "gif", "webp"];
const MAX_IMG = 6;
const MAX_BYTES = 5 * 1024 * 1024;

type Params = { objetivo: string; tamanho: string; idioma: string };
type Imagem = { nome: string; base64: string; url: string };

function lerBase64(f: Blob): Promise<string> {
  return new Promise((ok, falha) => {
    const r = new FileReader();
    r.onload = () => ok(String(r.result).split(",", 2)[1] ?? "");
    r.onerror = () => falha(r.error);
    r.readAsDataURL(f);
  });
}

function Parametros({ p, onChange }: { p: Params; onChange: (p: Params) => void }) {
  return (
    <div className="flex flex-col gap-3">
      <div role="radiogroup" aria-label="Objetivo do comentário" className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {OBJETIVOS.map((o) => {
          const ativo = p.objetivo === o.value;
          return (
            <button
              key={o.value}
              type="button"
              role="radio"
              aria-checked={ativo}
              onClick={() => onChange({ ...p, objetivo: o.value })}
              className={cn(
                "flex flex-col items-start gap-0.5 rounded-md border px-3 py-2 text-left transition-colors duration-fast",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
                ativo ? "border-primary bg-primary-soft text-primary-soft-fg" : "border-border bg-surface hover:border-border-strong",
              )}
            >
              <span className="text-sm font-medium">{o.label}</span>
              <span className={cn("text-xs", ativo ? "opacity-80" : "text-fg-subtle")}>{o.desc}</span>
            </button>
          );
        })}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Tamanho"><Select ariaLabel="Tamanho" value={p.tamanho} onValueChange={(v) => onChange({ ...p, tamanho: v })} options={OP_TAMANHO} /></Field>
        <Field label="Idioma"><Select ariaLabel="Idioma" value={p.idioma} onValueChange={(v) => onChange({ ...p, idioma: v })} options={OP_IDIOMA} /></Field>
      </div>
    </div>
  );
}

const PADRAO: Params = { objetivo: "acrescentar", tamanho: "curto", idioma: "auto" };

/** Formulário de um novo comentário: texto + imagens (colar, arrastar ou escolher). */
function NovoComentario() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [autor, setAutor] = useState("");
  const [plataforma, setPlataforma] = useState<PlataformaComentario>("linkedin");
  const [texto, setTexto] = useState("");
  const [imagens, setImagens] = useState<Imagem[]>([]);
  const [params, setParams] = useState<Params>(PADRAO);
  const [arrastando, setArrastando] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => () => imagens.forEach((i) => URL.revokeObjectURL(i.url)), []); // eslint-disable-line react-hooks/exhaustive-deps

  const adicionar = async (arquivos: File[]) => {
    const validos = arquivos.filter((f) => f.type.startsWith("image/"));
    if (!validos.length) return;
    const novas: Imagem[] = [];
    for (const f of validos) {
      if (imagens.length + novas.length >= MAX_IMG) { toast.error(`No máximo ${MAX_IMG} imagens.`); break; }
      const ext = (f.name.split(".").pop() || f.type.split("/")[1] || "png").toLowerCase();
      if (!EXT_OK.includes(ext)) { toast.error(`${f.name}: use PNG, JPG, GIF ou WEBP.`); continue; }
      if (f.size > MAX_BYTES) { toast.error(`${f.name}: maior que 5 MB.`); continue; }
      novas.push({ nome: `imagem-${imagens.length + novas.length + 1}.${ext}`, base64: await lerBase64(f), url: URL.createObjectURL(f) });
    }
    setImagens((atual) => [...atual, ...novas]);
  };

  // Colar print direto da área de transferência (Ctrl+V) em qualquer lugar da página.
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const arquivos = Array.from(e.clipboardData?.files ?? []);
      if (arquivos.some((f) => f.type.startsWith("image/"))) {
        e.preventDefault();
        void adicionar(arquivos);
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  });

  const criar = useMutation({
    mutationFn: () =>
      api.criarComentario({ autor, plataforma, texto_post: texto, imagens: imagens.map((i) => ({ nome: i.nome, conteudo_base64: i.base64 })) }),
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: ["comments"] });
      navigate(`/comentarios/${c.id}`, { state: { gerar: params } });
    },
    onError: (e: ApiError) => toast.error(e.message, { description: e.erro?.acao_sugerida ?? undefined }),
  });
  const pode = texto.trim().length > 0 || imagens.length > 0;
  const enviar = () => (pode ? criar.mutate() : toast.error("Cole o texto do post ou adicione uma imagem."));

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Novo comentário</h1>
        <p className="text-fg-muted">Cole o post de outra pessoa (texto e/ou prints) e receba 3 opções de comentário no seu estilo.</p>
      </div>
      <Card className="flex flex-col gap-4 p-5">
        <div role="radiogroup" aria-label="Plataforma" className="inline-flex w-fit gap-1 rounded-md border border-border bg-surface-2 p-1">
          {PLATAFORMAS.map((o) => (
            <button
              key={o.value}
              type="button"
              role="radio"
              aria-checked={plataforma === o.value}
              onClick={() => setPlataforma(o.value)}
              className={cn(
                "rounded px-3 py-1 text-sm transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
                plataforma === o.value ? "bg-surface font-medium text-fg shadow-sm" : "text-fg-muted hover:text-fg",
              )}
            >
              {o.label}
            </button>
          ))}
        </div>
        <Field label={plataforma === "medium" ? "Autor do artigo (opcional)" : "Autor do post (opcional)"} htmlFor="c-autor">
          <Input id="c-autor" value={autor} onChange={(e) => setAutor(e.target.value)} placeholder="Ex.: Ana Souza" maxLength={200} />
        </Field>
        <Field label={plataforma === "medium" ? "Texto do artigo" : "Texto do post"} htmlFor="c-texto" hint={plataforma === "medium" ? "Cole o artigo inteiro ou os trechos que quer comentar." : "Copie no LinkedIn com “…ver mais” aberto para pegar o texto inteiro."}>
          <Textarea
            id="c-texto"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); enviar(); } }}
            maxLength={10000}
            className="min-h-[180px] text-sm leading-relaxed"
            placeholder="Cole aqui o texto publicado…"
            autoFocus
          />
        </Field>
        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Imagens do post <span className="font-normal text-fg-subtle">(opcional)</span></span>
          <div
            onDragOver={(e) => { e.preventDefault(); setArrastando(true); }}
            onDragLeave={() => setArrastando(false)}
            onDrop={(e) => { e.preventDefault(); setArrastando(false); void adicionar(Array.from(e.dataTransfer.files)); }}
            className={cn("flex flex-wrap gap-3 rounded-lg border border-dashed border-border-strong p-3 transition-colors duration-fast", arrastando && "border-primary bg-primary-soft/40")}
          >
            <AnimatePresence initial={false}>
              {imagens.map((i) => (
                <motion.div key={i.nome} layout initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} className="group relative size-24 overflow-hidden rounded-md border border-border bg-surface-2">
                  <img src={i.url} alt={i.nome} className="size-full object-cover" />
                  <button
                    type="button"
                    aria-label={`Remover ${i.nome}`}
                    onClick={() => { URL.revokeObjectURL(i.url); setImagens(imagens.filter((x) => x !== i)); }}
                    className="absolute right-1 top-1 rounded-full bg-black/60 p-0.5 text-white opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100"
                  >
                    <X className="size-3.5" />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
            {imagens.length < MAX_IMG && (
              <button
                type="button"
                onClick={() => input.current?.click()}
                className="flex h-24 min-w-24 flex-1 flex-col items-center justify-center gap-1 rounded-md text-center text-fg-muted hover:bg-surface-2 hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              >
                <ImagePlus className="size-5" />
                <span className="text-sm font-medium">Cole um print (<Kbd>Ctrl</Kbd>+<Kbd>V</Kbd>), arraste ou clique</span>
                <span className="text-xs text-fg-subtle">Até {MAX_IMG} imagens · PNG, JPG, GIF ou WEBP</span>
              </button>
            )}
            <input ref={input} type="file" accept="image/*" multiple className="hidden" onChange={(e) => { void adicionar(Array.from(e.target.files ?? [])); e.target.value = ""; }} />
          </div>
        </div>
      </Card>
      <Card className="flex flex-col gap-4 p-5">
        <h2 className="font-semibold">Que tipo de comentário?</h2>
        <Parametros p={params} onChange={setParams} />
      </Card>
      <div className="flex items-center justify-end gap-3">
        <span className="hidden items-center gap-1 text-xs text-fg-subtle sm:inline-flex"><Kbd>Ctrl</Kbd>+<Kbd>Enter</Kbd></span>
        <Button variant="primary" size="lg" onClick={enviar} loading={criar.isPending}><Sparkles /> Gerar comentário</Button>
      </div>
    </motion.div>
  );
}

function SugestaoCard({ texto, abordagem, i, usada, onUsar, usando }: {
  texto: string; abordagem: string; i: number; usada: boolean; onUsar: () => void; usando: boolean;
}) {
  const [copiado, setCopiado] = useState(false);
  return (
    <motion.div variants={fadeUp} initial="hidden" animate="show" transition={{ delay: i * 0.06 }}>
      <Card className={cn("flex flex-col gap-3 p-4", usada && "border-primary")}>
        <div className="flex items-center justify-between gap-2">
          <span className="rounded-full bg-surface-2 px-2.5 py-0.5 text-xs font-medium text-fg-muted">{abordagem}</span>
          <span className="text-xs tabular-nums text-fg-subtle">{texto.length} caracteres</span>
        </div>
        <p className="whitespace-pre-wrap leading-relaxed">{texto}</p>
        <div className="flex items-center justify-end gap-2">
          {usada ? (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-primary"><CheckCheck className="size-3.5" /> Você usou esta</span>
          ) : (
            <Button size="sm" variant="ghost" onClick={onUsar} loading={usando}><CheckCheck /> Usei esta</Button>
          )}
          <Button
            size="sm"
            variant={copiado ? "soft" : "outline"}
            onClick={async () => {
              if (await copiar(texto)) { setCopiado(true); toast.success("Comentário copiado"); setTimeout(() => setCopiado(false), 2000); }
            }}
          >
            {copiado ? <Check /> : <Copy />} {copiado ? "Copiado" : "Copiar"}
          </Button>
        </div>
      </Card>
    </motion.div>
  );
}

function DetalheComentario({ id }: { id: number }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const c = useQuery({ queryKey: ["comment", id], queryFn: () => api.comentario(id) });
  const [params, setParams] = useState<Params>(PADRAO);
  const [instrucoes, setInstrucoes] = useState("");
  const iniciado = useRef(false);

  useEffect(() => {
    if (c.data?.parametros?.objetivo) setParams({ ...PADRAO, ...c.data.parametros } as Params);
  }, [c.data?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const gerar = useMutation({
    mutationFn: (p: { parametros: Params; instrucoes?: string }) => api.gerarComentario(id, p),
    onSuccess: (novo) => {
      qc.setQueryData(["comment", id], novo);
      qc.invalidateQueries({ queryKey: ["comments"] });
      setInstrucoes("");
    },
    onError: (e: ApiError) => {
      qc.invalidateQueries({ queryKey: ["comment", id] });
      toast.error(e.message, { description: e.erro?.acao_sugerida ?? undefined });
    },
  });
  const atualizar = (novo: Comentario) => {
    qc.setQueryData(["comment", id], novo);
    qc.invalidateQueries({ queryKey: ["comments"] });
  };
  const usar = useMutation({
    mutationFn: (indice: number) => api.marcarComentarioUsado(id, { indice }),
    onSuccess: (novo) => { atualizar(novo); toast.success("Marcado como usado"); },
    onError: (e: ApiError) => toast.error(e.message),
  });
  const voltar = useMutation({
    mutationFn: () => api.voltarComentarioSugerido(id),
    onSuccess: atualizar,
    onError: (e: ApiError) => toast.error(e.message),
  });
  const excluir = useMutation({
    mutationFn: () => api.excluirComentario(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["comments"] }); toast.success("Comentário excluído"); navigate("/comentarios"); },
  });

  // Vindo do formulário: gera logo ao abrir.
  useEffect(() => {
    const st = location.state as { gerar?: Params } | null;
    if (st?.gerar && !iniciado.current) {
      iniciado.current = true;
      setParams(st.gerar);
      gerar.mutate({ parametros: st.gerar });
      navigate(location.pathname, { replace: true, state: null });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (c.isError) return <p className="py-24 text-center text-fg-muted">Comentário não encontrado.</p>;
  if (!c.data) return <div className="space-y-4"><Skeleton className="h-10 w-1/2" /><Skeleton className="h-64" /></div>;
  const d: Comentario = c.data;

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {d.plataforma === "medium" ? (d.autor ? `Artigo de ${d.autor}` : "Artigo") : d.autor ? `Post de ${d.autor}` : "Post"}
            </h1>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-fg-muted">
              <Selos c={d} /> <span>Adicionado {relativo(d.criado_em)}</span>
              {d.link && <a href={d.link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-fg">Original <ExternalLink className="size-3" /></a>}
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={() => excluir.mutate()} loading={excluir.isPending}><Trash2 /> Excluir</Button>
        </div>
        <Card className="flex flex-col gap-3 p-4">
          {d.texto_post && <p className="max-h-[320px] overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed">{d.texto_post}</p>}
          {!!d.imagens.length && (
            <div className="flex flex-wrap gap-2">
              {d.imagens.map((n) => (
                <a key={n} href={api.imagemComentario(d.id, n)} target="_blank" rel="noreferrer" className="size-24 overflow-hidden rounded-md border border-border">
                  <img src={api.imagemComentario(d.id, n)} alt={n} className="size-full object-cover" />
                </a>
              ))}
            </div>
          )}
          {d.resumo_post && <p className="border-t border-border pt-3 text-xs text-fg-subtle">O Claude entendeu: {d.resumo_post}</p>}
        </Card>
        <Card className="flex flex-col gap-4 p-4">
          <Parametros p={params} onChange={setParams} />
          <Field label="Instruções extras (opcional)" htmlFor="c-instr">
            <Textarea id="c-instr" value={instrucoes} onChange={(e) => setInstrucoes(e.target.value)} maxLength={2000} className="min-h-[72px] text-sm" placeholder="Ex.: mencione que usei isso no meu último projeto; mais informal." />
          </Field>
          <Button variant={d.sugestoes.length ? "outline" : "primary"} onClick={() => gerar.mutate({ parametros: params, instrucoes })} loading={gerar.isPending}>
            {d.sugestoes.length ? <RefreshCw /> : <Sparkles />} {d.sugestoes.length ? "Gerar outras opções" : "Gerar comentário"}
          </Button>
        </Card>
      </div>
      <div className="flex flex-col gap-3" aria-live="polite">
        <h2 className="flex items-center gap-1.5 font-semibold"><MessageSquareText className="size-4 text-accent" /> Sugestões</h2>
        {gerar.isPending ? (
          <>
            <p className="text-sm text-fg-muted">{d.imagens.length ? "O Claude está lendo o post e as imagens…" : "O Claude está escrevendo…"}</p>
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-32" />)}
          </>
        ) : d.sugestoes.length ? (
          <>
            {d.status === "usado" && (
              <Card className="flex flex-col gap-2 p-3 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-1 font-medium"><CheckCheck className="size-4 text-primary" /> Comentário usado</span>
                  <Button size="sm" variant="ghost" onClick={() => voltar.mutate()} loading={voltar.isPending}><Undo2 /> Desfazer</Button>
                </div>
                {d.texto_final && d.escolhido === null && <p className="whitespace-pre-wrap text-fg-muted">{d.texto_final}</p>}
                {d.link_publicado && <a href={d.link_publicado} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-fg-muted hover:text-fg">Ver comentário publicado <ExternalLink className="size-3" /></a>}
              </Card>
            )}
            {d.sugestoes.map((s, i) => (
              <SugestaoCard key={`${d.gerado_em}-${i}`} i={i} texto={s.texto} abordagem={s.abordagem}
                usada={d.status === "usado" && d.escolhido === i} usando={usar.isPending && usar.variables === i} onUsar={() => usar.mutate(i)} />
            ))}
          </>
        ) : (
          <div className="rounded-lg border border-dashed border-border py-14 text-center text-sm text-fg-muted">
            {d.erro ? <span className="text-st-erro">{d.erro}</span> : "Escolha o tipo de comentário e gere as sugestões."}
          </div>
        )}
      </div>
    </div>
  );
}

export default function CommentsPage() {
  const params = useParams();
  const id = params.id ? Number(params.id) : null;
  const lista = useQuery({ queryKey: ["comments"], queryFn: api.comentarios });

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
      <aside className="flex flex-col gap-2">
        <Button asChild variant={id ? "outline" : "soft"} className="justify-start">
          <Link to="/comentarios"><Plus /> Novo comentário</Link>
        </Button>
        <div className="mt-2 text-xs font-medium uppercase tracking-wide text-fg-subtle">Histórico</div>
        {lista.isLoading ? (
          <Skeleton className="h-24" />
        ) : !lista.data?.length ? (
          <p className="text-sm text-fg-subtle">Nenhum comentário ainda.</p>
        ) : (
          <nav className="flex flex-col gap-1">
            {lista.data.map((c) => (
              <Link
                key={c.id}
                to={`/comentarios/${c.id}`}
                className={cn(
                  "rounded-md px-3 py-2 text-sm transition-colors duration-fast hover:bg-surface-2",
                  c.id === id ? "bg-surface-2 text-fg" : "text-fg-muted",
                )}
              >
                <span className="block truncate font-medium">{c.autor || c.texto_post.slice(0, 40) || "Post com imagens"}</span>
                <span className="block text-xs text-fg-subtle">
                  {NOME_PLATAFORMA[c.plataforma] ?? c.plataforma} · {relativo(c.criado_em)}
                  {c.status === "usado" ? " · usado" : c.sugestoes.length ? "" : " · sem sugestões"}
                </span>
              </Link>
            ))}
          </nav>
        )}
      </aside>
      <section className="min-w-0">{id ? <DetalheComentario key={id} id={id} /> : <NovoComentario />}</section>
    </div>
  );
}

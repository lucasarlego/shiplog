import { useEffect, useId, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "motion/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Clock, Folder, FolderGit2, GitBranch, Sparkles, Link2, PenLine } from "lucide-react";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";
import type { ApiErro, Job, Projeto } from "@/lib/types";
import { cn } from "@/lib/utils";
import { fadeUp } from "@/lib/motion";
import { relativo } from "@/lib/format";
import { Button } from "./ui/button";
import { Kbd } from "./ui/misc";
import { NewCommitsBadge, StatusBadge, ErrorBadge } from "./status";
import { JobStepper } from "./job";

type Modo = "repo" | "descrever";
const CHAVE_MODO = "shiplog.composer.modo";
const MIN_DESC = 20;
const MAX_DESC = 8000;

function lerModo(): Modo {
  try {
    return localStorage.getItem(CHAVE_MODO) === "descrever" ? "descrever" : "repo";
  } catch {
    return "repo";
  }
}

/** Compositor da tela inicial: com repositório ou a partir de uma descrição (spec 006, FR-01). */
export function Composer({ grande = false, podeGerar }: { grande?: boolean; podeGerar: boolean }) {
  const [params, setParams] = useSearchParams();
  const [focar, setFocar] = useState(params.get("modo") === "descrever");
  const [modo, setModoState] = useState<Modo>(() =>
    params.get("url") ? "repo" : params.get("modo") === "descrever" ? "descrever" : lerModo(),
  );
  const setModo = (m: Modo) => {
    setModoState(m);
    setFocar(true);
    try {
      localStorage.setItem(CHAVE_MODO, m);
    } catch {
      /* sem armazenamento: só não lembra a escolha */
    }
  };
  // Paleta: /?url=... força o modo repositório; /?modo=descrever abre o modo descrição.
  useEffect(() => {
    const m = params.get("modo");
    if (params.get("url")) setModoState("repo");
    else if (m === "descrever" || m === "repo") {
      setModo(m);
      setParams({}, { replace: true });
      if (m === "repo") setTimeout(() => document.getElementById("url-input")?.focus(), 50);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  return (
    <div className="w-full">
      <ModoToggle modo={modo} onChange={setModo} />
      <div className="mt-3">
        {modo === "repo" ? <UrlBar grande={grande} podeGerar={podeGerar} /> : <DescribeForm grande={grande} podeGerar={podeGerar} autoFocus={focar} />}
      </div>
    </div>
  );
}

function ModoToggle({ modo, onChange }: { modo: Modo; onChange: (m: Modo) => void }) {
  const id = useId();
  const opcoes: { value: Modo; label: string; icon: typeof Link2 }[] = [
    { value: "repo", label: "Repositório", icon: FolderGit2 },
    { value: "descrever", label: "Descrever", icon: PenLine },
  ];
  return (
    <div role="radiogroup" aria-label="Como começar o post" className="inline-flex rounded-lg border border-border bg-surface-2 p-0.5">
      {opcoes.map((o) => {
        const ativo = modo === o.value;
        const Icon = o.icon;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={ativo}
            onClick={() => onChange(o.value)}
            className={cn(
              "relative inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-sm font-medium transition-colors duration-fast",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
              ativo ? "text-fg" : "text-fg-muted hover:text-fg",
            )}
          >
            {ativo && (
              <motion.span layoutId={`modo-${id}`} className="absolute inset-0 rounded-md bg-surface shadow-sm" transition={{ type: "spring", bounce: 0.15, duration: 0.35 }} />
            )}
            <Icon className="relative size-4" />
            <span className="relative">{o.label}</span>
          </button>
        );
      })}
    </div>
  );
}

/** Modo Descrever: post sem repositório (spec 006, FR-02). */
function DescribeForm({ grande = false, podeGerar, autoFocus }: { grande?: boolean; podeGerar: boolean; autoFocus: boolean }) {
  const [titulo, setTitulo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [erro, setErro] = useState<ApiErro | null>(null);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const ref = useRef<HTMLTextAreaElement>(null);
  const tamanho = descricao.trim().length;

  useEffect(() => {
    if (autoFocus) ref.current?.focus();
  }, [autoFocus]);

  const criar = useMutation({
    mutationFn: () => api.criarProjeto({ descricao: descricao.trim(), nome: titulo.trim() || undefined, gerar: podeGerar }),
    onSuccess: (r) => {
      setTitulo("");
      setDescricao("");
      setErro(null);
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["jobs", "ativos"] });
      if (r.aviso) toast.warning("Post criado, mas a geração não começou", { description: r.aviso.mensagem });
      else toast.success(`${r.projeto.nome}`, { description: r.job ? "Escrevendo o post." : undefined });
      navigate(`/projetos/${r.projeto.id}`);
    },
    onError: (e: ApiError) => setErro(e.erro),
  });

  const enviar = () => {
    if (tamanho < MIN_DESC) {
      setErro({ codigo: "validacao", mensagem: `Descreva com pelo menos ${MIN_DESC} caracteres o que você quer contar.`, acao_sugerida: null });
      ref.current?.focus();
      return;
    }
    criar.mutate();
  };

  return (
    <div className="w-full text-left">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          enviar();
        }}
        className={cn(
          "rounded-xl border border-border bg-surface shadow-md transition-[border-color,box-shadow] duration-base",
          "focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/15",
          erro && "border-st-erro",
        )}
      >
        <input
          id="titulo-livre"
          value={titulo}
          onChange={(e) => setTitulo(e.target.value)}
          aria-label="Título (opcional)"
          placeholder="Título (opcional) — ex.: Migração do deploy para CI"
          maxLength={120}
          autoComplete="off"
          className="w-full border-b border-border bg-transparent px-4 py-3 font-medium outline-none placeholder:font-normal placeholder:text-fg-subtle"
        />
        <textarea
          id="descricao-input"
          ref={ref}
          value={descricao}
          onChange={(e) => {
            setDescricao(e.target.value);
            if (erro) setErro(null);
          }}
          onKeyDown={(e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
              e.preventDefault();
              enviar();
            }
          }}
          aria-label="O que você quer contar"
          aria-invalid={!!erro}
          aria-describedby={erro ? "descricao-erro" : undefined}
          maxLength={MAX_DESC}
          rows={grande ? 6 : 4}
          placeholder={
            "O que você fez e quer contar? Ex.: nesta semana conduzi a migração do deploy para um pipeline com revisão obrigatória; " +
            "o maior desafio foi convencer o time; aprendi que…"
          }
          className="block w-full resize-y bg-transparent px-4 py-3 leading-relaxed outline-none placeholder:text-fg-subtle"
        />
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-3 py-2">
          <span className={cn("text-xs tabular-nums", tamanho > 0 && tamanho < MIN_DESC ? "text-st-pronto" : "text-fg-subtle")}>
            {tamanho > 0 && tamanho < MIN_DESC ? `Mais ${MIN_DESC - tamanho} caracteres` : `${tamanho.toLocaleString("pt-BR")} / ${MAX_DESC.toLocaleString("pt-BR")}`}
            <span className="ml-2 hidden sm:inline">· Sem repositório: o Claude escreve só com base no seu texto.</span>
          </span>
          <div className="flex items-center gap-2">
            <span className="hidden items-center gap-1 text-xs text-fg-subtle sm:inline-flex">
              <Kbd>Ctrl</Kbd>+<Kbd>Enter</Kbd>
            </span>
            <Button type="submit" variant="primary" size={grande ? "lg" : "md"} loading={criar.isPending}>
              <Sparkles /> Gerar post
            </Button>
          </div>
        </div>
      </form>
      {erro && (
        <motion.div id="descricao-erro" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} className="mt-2 flex flex-wrap items-center gap-x-2 text-sm" role="alert">
          <span className="font-medium text-st-erro">{erro.mensagem}</span>
          {erro.acao_sugerida && <span className="text-fg-muted">{erro.acao_sugerida}</span>}
        </motion.div>
      )}
    </div>
  );
}

/** Campo de URL + Gerar (RF-01, RUI-15). */
function UrlBar({ grande = false, podeGerar }: { grande?: boolean; podeGerar: boolean }) {
  const [url, setUrl] = useState("");
  const [erro, setErro] = useState<ApiErro | null>(null);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const inputRef = useRef<HTMLInputElement>(null);

  const criar = useMutation({
    mutationFn: (u: string) => api.criarProjeto({ url: u, gerar: podeGerar }),
    onSuccess: (r) => {
      setUrl("");
      setErro(null);
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["jobs", "ativos"] });
      if (r.aviso) toast.warning("Projeto cadastrado, mas a geração não começou", { description: r.aviso.mensagem });
      else toast.success(`${r.projeto.nome} cadastrado`, { description: r.job ? "Geração do post iniciada." : undefined });
      navigate(`/projetos/${r.projeto.id}`);
    },
    onError: (e: ApiError) => setErro(e.erro),
  });

  // Paleta de comandos: /?url=... preenche e gera.
  useEffect(() => {
    const u = params.get("url");
    if (u) {
      setUrl(u);
      setParams({}, { replace: true });
      criar.mutate(u);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const enviar = () => {
    if (!url.trim()) {
      setErro({ codigo: "url_invalida", mensagem: "Cole a URL de um repositório Git.", acao_sugerida: null });
      inputRef.current?.focus();
      return;
    }
    criar.mutate(url.trim());
  };

  return (
    <div className="w-full">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          enviar();
        }}
        className={cn(
          "flex items-center gap-2 rounded-xl border border-border bg-surface p-1.5 shadow-md transition-[border-color,box-shadow] duration-base",
          "focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/15",
          erro && "border-st-erro",
        )}
      >
        <Link2 className="ml-2.5 size-5 shrink-0 text-fg-subtle" />
        <input
          id="url-input"
          ref={inputRef}
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            if (erro) setErro(null);
          }}
          aria-label="URL do repositório"
          aria-invalid={!!erro}
          aria-describedby={erro ? "url-erro" : undefined}
          placeholder="Cole a URL do repositório — https://github.com/voce/projeto ou git@github.com:voce/projeto.git"
          className={cn("min-w-0 flex-1 bg-transparent px-1 outline-none placeholder:text-fg-subtle", grande ? "h-11 text-md" : "h-9 text-base")}
          autoComplete="off"
          spellCheck={false}
        />
        {!url && <Kbd className="mr-1">/</Kbd>}
        <Button type="submit" variant="primary" size={grande ? "lg" : "md"} loading={criar.isPending}>
          <Sparkles /> Gerar post
        </Button>
      </form>
      {erro && (
        <motion.div id="url-erro" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} className="mt-2 flex flex-wrap items-center gap-x-2 text-sm" role="alert">
          <span className="font-medium text-st-erro">{erro.mensagem}</span>
          {erro.acao_sugerida && <span className="text-fg-muted">{erro.acao_sugerida}</span>}
          {erro.codigo === "projeto_duplicado" && typeof erro.detalhes?.projeto_id === "number" && (
            <Link className="font-medium text-primary underline-offset-2 hover:underline" to={`/projetos/${erro.detalhes.projeto_id}`}>
              Abrir projeto
            </Link>
          )}
        </motion.div>
      )}
    </div>
  );
}

export function ProjectCard({ p, job }: { p: Projeto; job?: Job }) {
  const ativo = job ?? null;
  const livre = p.origem === "livre";
  const local = p.origem === "local";
  const Icone = livre ? PenLine : local ? Folder : FolderGit2;
  return (
    <motion.div variants={fadeUp} layout="position">
      <Link
        to={`/projetos/${p.id}`}
        className={cn(
          "group flex h-full flex-col gap-3 rounded-lg border border-border bg-surface p-4 shadow-sm",
          "transition-[border-color,box-shadow,transform] duration-base ease-out hover:-translate-y-0.5 hover:border-border-strong hover:shadow-md motion-reduce:hover:translate-y-0",
          ativo && "border-grad border shadow-md",
        )}
      >
        <div className="flex items-start gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-surface-2 text-fg-muted">
            <Icone className="size-4.5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate font-semibold tracking-tight">{p.nome}</div>
            <div className="truncate text-xs text-fg-subtle">
              {livre ? "Sem repositório" : local ? (p.caminho_local ?? "Pasta local") : (p.url_repo ?? "").replace(/^https?:\/\//, "")}
            </div>
          </div>
          <ArrowRight className="size-4 shrink-0 text-fg-subtle opacity-0 transition-opacity duration-fast group-hover:opacity-100" />
        </div>
        {livre && p.descricao && <p className="line-clamp-2 text-sm text-fg-muted">{p.descricao}</p>}
        <div className="flex flex-wrap items-center gap-1.5">
          <StatusBadge status={p.ultimo_post?.status} />
          {p.commits_novos && <NewCommitsBadge />}
          {p.ultimo_artigo && (
            <span className="inline-flex items-center gap-1 rounded-full bg-surface-2 px-2 py-0.5 text-xs text-fg-muted">
              Artigo · {p.ultimo_artigo.status}
            </span>
          )}
        </div>
        <div className="mt-auto flex items-center justify-between gap-2 text-xs text-fg-subtle">
          {ativo ? (
            ativo.status === "erro" ? <ErrorBadge /> : <JobStepper job={ativo} compact livre={livre} />
          ) : (
            <span className="inline-flex items-center gap-1">
              <Clock className="size-3.5" />{" "}
              {p.ultima_analise_em
                ? `${livre ? "Gerado" : "Analisado"} ${relativo(p.ultima_analise_em)}`
                : livre ? "Ainda não gerado" : "Ainda não analisado"}
            </span>
          )}
          {p.branch && (
            <span className="inline-flex items-center gap-1 font-mono">
              <GitBranch className="size-3.5" /> {p.branch}
            </span>
          )}
        </div>
      </Link>
    </motion.div>
  );
}

export function EmptyState({ podeGerar }: { podeGerar: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto flex max-w-2xl flex-col items-center py-16 text-center"
    >
      <div className="mb-6 flex size-14 items-center justify-center rounded-xl bg-primary-soft text-primary-soft-fg shadow-sm">
        <Sparkles className="size-6" />
      </div>
      <h1 className="text-3xl font-semibold tracking-tight">Do que você fez ao post em minutos</h1>
      <p className="mt-3 max-w-lg text-md text-fg-muted">
        Cole a URL de um projeto seu — o Claude Code lê o código (só leitura) — ou simplesmente descreva o que fez na semana.
        Você recebe um rascunho de post para o LinkedIn, revisa, copia e publica.
      </p>
      <div className="mt-8 flex w-full flex-col items-center">
        <Composer grande podeGerar={podeGerar} />
      </div>
      <p className="mt-4 text-xs text-fg-subtle">
        Repositórios: GitHub, GitLab ou qualquer remoto Git que o seu git local já acessa (HTTPS ou SSH).
      </p>
    </motion.div>
  );
}

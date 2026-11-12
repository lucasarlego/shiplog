import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { ArrowLeft, ExternalLink, FileText, GitBranch, GitCommitHorizontal, Megaphone, Pencil, PenLine, StickyNote, Trash2, Check } from "lucide-react";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";
import type { Artigo, Job, Post, Projeto, TipoGeracao } from "@/lib/types";
import { useHealth, useJobsAtivos } from "@/lib/hooks";
import { relativo } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Card, Skeleton, Switch } from "@/components/ui/misc";
import { Dialog } from "@/components/ui/dialog";
import { TabsList } from "@/components/ui/tabs";
import { NewCommitsBadge, StatusBadge } from "@/components/status";
import { AvisosJob, JobError, JobStepper } from "@/components/job";
import { GenerationPanel } from "@/components/generation";
import { CompareDialog, VersionList } from "@/components/versions";
import { PostEditor } from "@/components/post";
import { ArticleEditor } from "@/components/article";

function useDebouncedSave(valor: string, original: string, salvar: (v: string) => void, ms = 800) {
  useEffect(() => {
    if (valor === original) return;
    const t = setTimeout(() => salvar(valor), ms);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [valor]);
}

function Header({ p }: { p: Projeto }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [editNome, setEditNome] = useState(false);
  const [nome, setNome] = useState(p.nome);
  const [branchOpen, setBranchOpen] = useState(false);
  const [branch, setBranch] = useState(p.branch ?? "");
  const [delOpen, setDelOpen] = useState(false);
  const [manter, setManter] = useState(false);
  const livre = p.origem === "livre";
  const url = p.url_repo ?? "";
  const editar = useMutation({
    mutationFn: (b: { nome?: string; branch?: string }) => api.editarProjeto(p.id, b),
    onSuccess: (np) => {
      qc.setQueryData(["project", p.id], np);
      qc.invalidateQueries({ queryKey: ["projects"] });
      setEditNome(false);
      setBranchOpen(false);
      toast.success("Projeto atualizado");
    },
    onError: (e: ApiError) => toast.error(e.message, { description: e.erro.acao_sugerida ?? undefined }),
  });
  const excluir = useMutation({
    mutationFn: () => api.excluirProjeto(p.id, manter),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      toast.success(manter ? "Projeto arquivado (histórico mantido)" : "Projeto excluído");
      navigate("/");
    },
    onError: (e: ApiError) => toast.error(e.message, { description: e.erro.acao_sugerida ?? undefined }),
  });

  return (
    <div className="flex items-start gap-4">
      <Button variant="ghost" size="icon" onClick={() => navigate("/")} aria-label="Voltar ao painel">
        <ArrowLeft />
      </Button>
      <div className="min-w-0 flex-1">
        {editNome ? (
          <form className="flex items-center gap-2" onSubmit={(e) => { e.preventDefault(); editar.mutate({ nome }); }}>
            <Input value={nome} onChange={(e) => setNome(e.target.value)} className="h-9 max-w-sm text-lg font-semibold" autoFocus aria-label="Nome do projeto" />
            <Button size="sm" variant="soft" type="submit" loading={editar.isPending}><Check /> Salvar</Button>
            <Button size="sm" variant="ghost" type="button" onClick={() => { setNome(p.nome); setEditNome(false); }}>Cancelar</Button>
          </form>
        ) : (
          <div className="group flex items-center gap-2">
            <h1 className="truncate text-2xl font-semibold tracking-tight">{p.nome}</h1>
            <Button size="icon-sm" variant="ghost" onClick={() => setEditNome(true)} aria-label="Editar nome" className="opacity-0 group-hover:opacity-100 focus:opacity-100">
              <Pencil />
            </Button>
          </div>
        )}
        {livre ? (
          <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-fg-muted">
            <span className="inline-flex items-center gap-1"><PenLine className="size-3.5" /> Sem repositório</span>
            <span className="text-xs">{p.ultima_analise_em ? `Gerado ${relativo(p.ultima_analise_em)}` : "Ainda não gerado"}</span>
          </div>
        ) : (
        <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-fg-muted">
          <a href={url.startsWith("http") ? url : undefined} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 truncate hover:text-fg">
            {url} {url.startsWith("http") && <ExternalLink className="size-3" />}
          </a>
          <button onClick={() => setBranchOpen(true)} className="inline-flex items-center gap-1 font-mono text-xs hover:text-fg" aria-label="Alterar branch">
            <GitBranch className="size-3.5" /> {p.branch ?? "branch padrão"}
          </button>
          {p.commit_analisado && (
            <span className="inline-flex items-center gap-1 font-mono text-xs">
              <GitCommitHorizontal className="size-3.5" /> {p.commit_analisado.slice(0, 7)}
            </span>
          )}
          <span className="text-xs">Analisado {relativo(p.ultima_analise_em)}</span>
          {p.commits_novos && <NewCommitsBadge />}
        </div>
        )}
      </div>
      <Button variant="ghost" size="sm" onClick={() => setDelOpen(true)}>
        <Trash2 /> Excluir
      </Button>

      <Dialog open={branchOpen} onOpenChange={setBranchOpen} title="Branch analisada" description="Deixe em branco para usar a branch padrão do remoto. Trocar a branch recria o clone na próxima geração.">
        <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); editar.mutate({ branch }); }}>
          <Input value={branch} onChange={(e) => setBranch(e.target.value)} placeholder="main" className="font-mono" autoFocus aria-label="Branch" />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setBranchOpen(false)}>Cancelar</Button>
            <Button type="submit" variant="primary" loading={editar.isPending}>Salvar</Button>
          </div>
        </form>
      </Dialog>
      <Dialog open={delOpen} onOpenChange={setDelOpen} title={`Excluir ${p.nome}?`} description={livre ? "Os posts gerados a partir desta descrição serão apagados." : "O clone local será removido. Nada é apagado no repositório remoto."}>
        <div className="flex flex-col gap-4">
          <label className="flex items-center justify-between gap-3 rounded-md border border-border p-3 text-sm">
            <span>
              Manter histórico de posts e artigos
              <span className="block text-xs text-fg-subtle">O projeto some do painel, mas continua na exportação.</span>
            </span>
            <Switch checked={manter} onCheckedChange={setManter} />
          </label>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setDelOpen(false)}>Cancelar</Button>
            <Button variant="danger" onClick={() => excluir.mutate()} loading={excluir.isPending}>
              <Trash2 /> {manter ? "Arquivar" : "Excluir tudo"}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}

function Notes({ p }: { p: Projeto }) {
  const qc = useQueryClient();
  const [notas, setNotas] = useState(p.notas);
  const [salvo, setSalvo] = useState(true);
  const salvar = useMutation({
    mutationFn: (n: string) => api.editarProjeto(p.id, { notas: n }),
    onSuccess: (np) => {
      qc.setQueryData(["project", p.id], np);
      setSalvo(true);
    },
    onError: (e: ApiError) => toast.error(e.message),
  });
  useDebouncedSave(notas, p.notas, (v) => salvar.mutate(v));
  return (
    <Card className="p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-sm font-medium"><StickyNote className="size-4 text-accent" /> Notas do projeto</span>
        <span className="text-xs text-fg-subtle" aria-live="polite">{salvar.isPending ? "Salvando…" : salvo ? "Salvo" : "Editando…"}</span>
      </div>
      <Textarea
        value={notas}
        onChange={(e) => { setNotas(e.target.value); setSalvo(false); }}
        placeholder="Contexto que não está no código. Ex.: fiz isso para um cliente; o foco é a arquitetura."
        className="min-h-[88px] text-sm"
        aria-label="Notas do projeto"
      />
    </Card>
  );
}

/** Projeto sem repositório: a descrição é a fonte do post (spec 006, FR-08). */
function DescriptionCard({ p }: { p: Projeto }) {
  const qc = useQueryClient();
  const [desc, setDesc] = useState(p.descricao);
  const [salvo, setSalvo] = useState(true);
  const curta = desc.trim().length < 20;
  const salvar = useMutation({
    mutationFn: (d: string) => api.editarProjeto(p.id, { descricao: d }),
    onSuccess: (np) => {
      qc.setQueryData(["project", p.id], np);
      qc.invalidateQueries({ queryKey: ["projects"] });
      setSalvo(true);
    },
    onError: (e: ApiError) => toast.error(e.message),
  });
  useDebouncedSave(desc, p.descricao, (v) => { if (v.trim().length >= 20) salvar.mutate(v); });
  return (
    <Card className="p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-sm font-medium"><PenLine className="size-4 text-accent" /> Sobre o que é o post</span>
        <span className={curta ? "text-xs text-st-erro" : "text-xs text-fg-subtle"} aria-live="polite">
          {curta ? "Mínimo de 20 caracteres" : salvar.isPending ? "Salvando…" : salvo ? "Salvo · regenere para usar a nova versão" : "Editando…"}
        </span>
      </div>
      <Textarea
        value={desc}
        onChange={(e) => { setDesc(e.target.value); setSalvo(false); }}
        maxLength={8000}
        className="min-h-[120px] text-sm leading-relaxed"
        aria-label="Descrição do post"
      />
    </Card>
  );
}

function Workspace<T extends Post | Artigo>({
  projeto,
  tipo,
  versoes,
  carregando,
  jobAtivo,
  ultimoJob,
}: {
  projeto: Projeto;
  tipo: TipoGeracao;
  versoes: T[] | undefined;
  carregando: boolean;
  jobAtivo: Job | undefined;
  ultimoJob: Job | undefined;
}) {
  const health = useHealth();
  const [sel, setSel] = useState<number | null>(null);
  const [comparar, setComparar] = useState(false);
  const [recem, setRecem] = useState<number | null>(null);
  const jobVisto = useRef<number | null>(null);

  // Ao concluir uma geração, seleciona a nova versão e anima a revelação (RUI-10).
  useEffect(() => {
    if (ultimoJob?.status === "concluido" && ultimoJob.resultado_id && jobVisto.current !== ultimoJob.id) {
      if (jobVisto.current !== null) {
        setSel(ultimoJob.resultado_id);
        setRecem(ultimoJob.resultado_id);
      }
      jobVisto.current = ultimoJob.id;
    } else if (ultimoJob && jobVisto.current === null) {
      jobVisto.current = ultimoJob.id;
    }
  }, [ultimoJob]);

  const atual = useMemo(() => versoes?.find((v) => v.id === sel) ?? versoes?.[0], [versoes, sel]);
  const mostrarErro =
    !jobAtivo && ultimoJob && (ultimoJob.status === "erro" || ultimoJob.status === "cancelado") &&
    (!versoes?.length || new Date(ultimoJob.criado_em) > new Date(versoes[0].criado_em));

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
      <aside className="flex flex-col gap-4">
        <GenerationPanel
          projeto={projeto}
          tipo={tipo}
          health={health.data}
          baseVersaoId={atual?.id ?? null}
          temVersoes={!!versoes?.length}
          jobAtivo={!!jobAtivo}
          onStarted={() => { jobVisto.current = jobVisto.current ?? -1; }}
        />
        {!!versoes?.length && (
          <VersionList versoes={versoes} selecionada={atual?.id ?? null} onSelect={(id) => { setSel(id); setRecem(null); }} onCompare={() => setComparar(true)} />
        )}
      </aside>
      <section className="flex min-w-0 flex-col gap-4">
        {jobAtivo && <JobStepper job={jobAtivo} livre={projeto.origem === "livre"} />}
        {mostrarErro && ultimoJob && <JobError job={ultimoJob} />}
        {ultimoJob?.status === "concluido" && atual?.geracao_id === ultimoJob.id && <AvisosJob avisos={ultimoJob.avisos} />}
        {carregando ? (
          <div className="space-y-3"><Skeleton className="h-10 w-2/3" /><Skeleton className="h-72" /></div>
        ) : atual ? (
          tipo === "post" ? (
            <PostEditor post={atual as Post} novo={recem === atual.id} />
          ) : (
            <ArticleEditor artigo={atual as Artigo} novo={recem === atual.id} />
          )
        ) : (
          !jobAtivo && !mostrarErro && (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-20 text-center">
              {tipo === "post" ? <Megaphone className="mb-3 size-8 text-fg-subtle" /> : <FileText className="mb-3 size-8 text-fg-subtle" />}
              <p className="font-medium">{tipo === "post" ? "Nenhum post ainda" : "Nenhum artigo ainda"}</p>
              <p className="mt-1 max-w-sm text-sm text-fg-muted">
                {tipo === "post"
                  ? "Escolha os parâmetros ao lado e gere o primeiro rascunho."
                  : "Gere um artigo para o Medium com trechos reais do código, usando a skill medium-article-writer."}
              </p>
            </div>
          )
        )}
      </section>
      {versoes && versoes.length > 1 && (
        <CompareDialog
          open={comparar}
          onOpenChange={setComparar}
          versoes={versoes}
          render={(v) => ("texto" in v ? `${v.texto}\n\n${v.hashtags.join(" ")}` : `# ${(v as Artigo).titulo}\n\n${(v as Artigo).corpo_markdown}`)}
        />
      )}
    </div>
  );
}

export default function ProjectPage() {
  const id = Number(useParams().id);
  const [aba, setAba] = useState<"post" | "artigo">("post");
  const jobs = useJobsAtivos();
  const projeto = useQuery({ queryKey: ["project", id], queryFn: () => api.projeto(id) });
  const posts = useQuery({ queryKey: ["posts", id], queryFn: () => api.posts(id) });
  const artigos = useQuery({ queryKey: ["articles", id], queryFn: () => api.artigos(id) });
  const geracoes = useQuery({ queryKey: ["geracoes", id], queryFn: () => api.geracoes(id) });
  const ativos = (jobs.data ?? []).filter((j) => j.projeto_id === id);

  useEffect(() => {
    if (ativos.length) geracoes.refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ativos.map((j) => `${j.id}${j.status}`).join()]);

  if (projeto.isError) {
    const e = projeto.error as ApiError;
    return (
      <div className="py-24 text-center">
        <p className="text-lg font-medium">{e.erro?.codigo === "nao_encontrado" ? "Projeto não encontrado." : e.message}</p>
        <Button className="mt-4" onClick={() => history.back()}>Voltar</Button>
      </div>
    );
  }
  if (!projeto.data) {
    return <div className="space-y-4"><Skeleton className="h-12 w-1/2" /><Skeleton className="h-28" /><Skeleton className="h-96" /></div>;
  }
  const p = projeto.data;
  const ultimo = (t: TipoGeracao) => geracoes.data?.find((g) => g.tipo === t);
  const livre = p.origem === "livre";

  return (
    <div className="flex flex-col gap-6">
      <Header p={p} />
      {livre ? <DescriptionCard key={p.id} p={p} /> : <Notes key={p.id} p={p} />}
      <TabsPrimitive.Root value={aba} onValueChange={(v) => setAba(v as "post" | "artigo")} className="flex flex-col gap-5">
        <TabsList
          layoutId="aba-projeto"
          value={aba}
          items={[
            { value: "post", label: "Post do LinkedIn", icon: <Megaphone />, badge: posts.data?.[0] && <StatusBadge status={posts.data[0].status} className="ml-1" /> },
            { value: "artigo", label: "Artigo do Medium", icon: <FileText />, disabled: livre, hint: livre ? "Artigos precisam de um repositório: eles citam trechos reais de código." : undefined, badge: artigos.data?.[0] && <StatusBadge status={artigos.data[0].status} className="ml-1" /> },
          ]}
        />
        <TabsPrimitive.Content value="post" className="focus:outline-none">
          <Workspace projeto={p} tipo="post" versoes={posts.data} carregando={posts.isLoading} jobAtivo={ativos.find((j) => j.tipo === "post")} ultimoJob={ultimo("post")} />
        </TabsPrimitive.Content>
        <TabsPrimitive.Content value="artigo" className="focus:outline-none">
          <Workspace projeto={p} tipo="artigo" versoes={artigos.data} carregando={artigos.isLoading} jobAtivo={ativos.find((j) => j.tipo === "artigo")} ultimoJob={ultimo("artigo")} />
        </TabsPrimitive.Content>
      </TabsPrimitive.Root>
    </div>
  );
}

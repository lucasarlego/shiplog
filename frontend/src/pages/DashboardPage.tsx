import { useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleDashed, CircleDot, CheckCircle2, GitCommitHorizontal, LayoutGrid, Send } from "lucide-react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { api } from "@/lib/api";
import { useHealth, useJobsAtivos } from "@/lib/hooks";
import { stagger } from "@/lib/motion";
import { Composer, EmptyState, ProjectCard } from "@/components/dashboard";
import { TabsList } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/misc";
import { Button } from "@/components/ui/button";

const FILTROS = [
  { value: "", label: "Todos", icon: <LayoutGrid /> },
  { value: "sem_post", label: "Sem post", icon: <Send /> },
  { value: "rascunho", label: "Rascunho", icon: <CircleDashed /> },
  { value: "pronto", label: "Pronto", icon: <CircleDot /> },
  { value: "publicado", label: "Publicado", icon: <CheckCircle2 /> },
  { value: "commits_novos", label: "Commits novos", icon: <GitCommitHorizontal /> },
];

let ultimoCheck = 0;

export default function DashboardPage() {
  const [filtro, setFiltro] = useState("");
  const qc = useQueryClient();
  const health = useHealth();
  const jobs = useJobsAtivos();
  const todos = useQuery({ queryKey: ["projects", ""], queryFn: () => api.projetos() });
  const filtrados = useQuery({
    queryKey: ["projects", filtro],
    queryFn: () => api.projetos(filtro || undefined),
    enabled: !!filtro,
  });
  const lista = filtro ? filtrados.data : todos.data;
  const jobPorProjeto = useMemo(() => new Map((jobs.data ?? []).map((j) => [j.projeto_id, j])), [jobs.data]);
  const podeGerar = health.data?.pode_gerar_post ?? true;

  // RF-10: verifica commits novos ao abrir o painel (no máximo a cada 5 min).
  useEffect(() => {
    if (!todos.data?.length || Date.now() - ultimoCheck < 5 * 60_000) return;
    ultimoCheck = Date.now();
    api.checkUpdates().then(() => qc.invalidateQueries({ queryKey: ["projects"] })).catch(() => undefined);
  }, [todos.data?.length, qc]);

  if (todos.isError) {
    return (
      <div className="py-24 text-center">
        <p className="text-lg font-medium">Não foi possível carregar os projetos.</p>
        <p className="mt-1 text-fg-muted">{(todos.error as Error).message}</p>
        <Button className="mt-4" onClick={() => todos.refetch()}>Tentar novamente</Button>
      </div>
    );
  }

  if (todos.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-14 w-full" />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-36" />)}
        </div>
      </div>
    );
  }

  if (!todos.data?.length) return <EmptyState podeGerar={podeGerar} />;

  return (
    <div className="space-y-8">
      <section>
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Seus projetos</h1>
        <p className="mb-5 text-fg-muted">Cole um repositório, descreva o que você fez ou abra um projeto para revisar o post.</p>
        <Composer podeGerar={podeGerar} />
      </section>
      <section className="space-y-4">
        <TabsPrimitive.Root value={filtro} onValueChange={setFiltro}>
          <TabsList layoutId="filtro-painel" value={filtro} items={FILTROS} />
        </TabsPrimitive.Root>
        {lista === undefined ? (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-36" />)}
          </div>
        ) : lista.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border py-14 text-center text-fg-muted">
            Nenhum projeto com este status.
          </div>
        ) : (
          <motion.div
            key={filtro}
            className="grid grid-cols-2 gap-4 lg:grid-cols-3"
            initial="hidden"
            animate="show"
            variants={{ show: { transition: { staggerChildren: stagger } } }}
          >
            {lista.map((p) => <ProjectCard key={p.id} p={p} job={jobPorProjeto.get(p.id)} />)}
          </motion.div>
        )}
      </section>
    </div>
  );
}

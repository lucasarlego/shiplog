import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Download, RefreshCw, Save, XCircle, RotateCcw, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";
import type { CheckItem, Config } from "@/lib/types";
import { baixar, cn } from "@/lib/utils";
import { dataHora } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Card, Field, Skeleton } from "@/components/ui/misc";
import { Select } from "@/components/ui/select";
import { ProfileCard } from "@/components/profile";
import { OP_FORMATO, OP_IDIOMA, OP_PUBLICO, OP_TAMANHO, OP_TOM } from "@/components/generation";

function Check({ titulo, item, extra }: { titulo: string; item: CheckItem; extra?: string | null }) {
  return (
    <div className="flex items-start gap-3 py-3">
      {item.ok ? <CheckCircle2 className="mt-0.5 size-5 text-st-publicado" /> : <XCircle className="mt-0.5 size-5 text-st-erro" />}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 font-medium">
          {titulo}
          <span className={cn("text-xs font-normal", item.ok ? "text-st-publicado" : "text-st-erro")}>{item.ok ? "OK" : "Problema"}</span>
        </div>
        {extra && <div className="truncate font-mono text-xs text-fg-subtle">{extra}</div>}
        {item.mensagem && <div className="text-sm text-fg-muted">{item.mensagem}</div>}
        {item.comando_sugerido && <div className="mt-1 rounded-sm bg-surface-2 px-2 py-1 font-mono text-xs">{item.comando_sugerido}</div>}
      </div>
    </div>
  );
}

function HealthPanel() {
  const qc = useQueryClient();
  const h = useQuery({ queryKey: ["health"], queryFn: api.health });
  const refresh = useMutation({ mutationFn: api.healthRefresh, onSuccess: (d) => qc.setQueryData(["health"], d) });
  return (
    <Card className="p-5">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="font-semibold">Verificação do Claude Code</h2>
        <Button size="sm" variant="outline" onClick={() => refresh.mutate()} loading={refresh.isPending}><RefreshCw /> Verificar</Button>
      </div>
      {!h.data ? (
        <Skeleton className="h-40" />
      ) : (
        <div className="divide-y divide-border">
          <Check titulo="Claude Code CLI" item={h.data.cli} extra={h.data.cli.caminho && `${h.data.cli.caminho} · v${h.data.cli.versao ?? "?"}`} />
          <Check titulo="Login (assinatura)" item={h.data.auth} extra={h.data.auth.metodo && `${h.data.auth.metodo}${h.data.auth.plano ? ` · plano ${h.data.auth.plano}` : ""}`} />
          <Check titulo="Skill medium-article-writer" item={h.data.skill} />
          <Check titulo="git" item={h.data.git} extra={h.data.git.versao} />
          <p className="pt-3 text-xs text-fg-subtle">Verificado {dataHora(h.data.verificado_em)}. O Shiplog usa só o CLI logado — nenhuma chamada à API paga.</p>
        </div>
      )}
    </Card>
  );
}

const perfilDe = (c: Config) => ({
  perfil_profissional: c.perfil_profissional,
  perfil_sobre: c.perfil_sobre,
  curriculo_nome: c.curriculo_nome,
  perfil_gerado_em: c.perfil_gerado_em,
});

export default function SettingsPage() {
  const qc = useQueryClient();
  const cfg = useQuery({ queryKey: ["settings"], queryFn: api.config });
  const [f, setF] = useState<Config | null>(null);
  // Os campos do perfil (spec 007) são salvos pelo próprio cartão; o formulário só acompanha.
  useEffect(() => {
    const d = cfg.data;
    if (!d) return;
    setF((prev) => (prev ? { ...prev, ...perfilDe(d) } : d));
  }, [cfg.data]);
  const salvar = useMutation({
    // O perfil tem salvamento próprio; não sobrescreve com uma cópia antiga do formulário.
    mutationFn: ({ perfil_profissional: _p, perfil_sobre: _s, curriculo_nome: _c, perfil_gerado_em: _g, ...c }: Config) => api.salvarConfig(c),
    onSuccess: (c) => {
      qc.setQueryData(["settings"], c);
      qc.invalidateQueries({ queryKey: ["health"] });
      toast.success("Configurações salvas");
    },
    onError: (e: ApiError) => toast.error(e.message, { description: e.erro.acao_sugerida ?? undefined }),
  });
  if (!f || !cfg.data) return <div className="space-y-4"><Skeleton className="h-10 w-64" /><Skeleton className="h-96" /></div>;
  const sujo = JSON.stringify(f) !== JSON.stringify(cfg.data);
  const set = <K extends keyof Config>(k: K, v: Config[K]) => setF({ ...f, [k]: v });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Configurações</h1>
          <p className="text-fg-muted">Prompt, voz, caminhos e padrões usados em todas as gerações.</p>
        </div>
        <Button variant="primary" onClick={() => salvar.mutate(f)} loading={salvar.isPending} disabled={!sujo}><Save /> Salvar</Button>
      </div>
      {cfg.data.reinicio_necessario && (
        <div className="flex items-center gap-2 rounded-md bg-st-novos-soft px-3 py-2 text-sm text-st-novos" role="status">
          <AlertTriangle className="size-4" /> Pasta de dados alterada. Reinicie o Shiplog e mova os arquivos manualmente, se quiser manter o histórico.
        </div>
      )}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="flex flex-col gap-6">
          <ProfileCard cfg={cfg.data} />
          <Card className="flex flex-col gap-4 p-5">
            <h2 className="font-semibold">Escrita</h2>
            <Field label="Prompt base" htmlFor="prompt-base" hint="Instruções gerais para o redator de posts. Os dados do projeto e o formato da resposta são adicionados automaticamente.">
              <Textarea id="prompt-base" value={f.prompt_base} onChange={(e) => set("prompt_base", e.target.value)} className="min-h-[220px] font-mono text-sm" />
            </Field>
            <Field label="Perfil de voz" htmlFor="voz" hint="Estilo: como você escreve e expressões que evita. Quem você é fica no Perfil profissional, acima.">
              <Textarea id="voz" value={f.perfil_voz} onChange={(e) => set("perfil_voz", e.target.value)} className="min-h-[110px] text-sm" placeholder="Ex.: escrevo de forma direta, sem emojis; gosto de falar de arquitetura de dados e GCP." />
            </Field>
          </Card>
          <Card className="flex flex-col gap-4 p-5">
            <h2 className="font-semibold">Parâmetros padrão</h2>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Tom do post"><Select ariaLabel="Tom padrão" value={f.parametros_padrao_post.tom} onValueChange={(v) => set("parametros_padrao_post", { ...f.parametros_padrao_post, tom: v })} options={OP_TOM} /></Field>
              <Field label="Tamanho do post"><Select ariaLabel="Tamanho padrão" value={f.parametros_padrao_post.tamanho} onValueChange={(v) => set("parametros_padrao_post", { ...f.parametros_padrao_post, tamanho: v })} options={OP_TAMANHO} /></Field>
              <Field label="Idioma do post"><Select ariaLabel="Idioma padrão do post" value={f.parametros_padrao_post.idioma} onValueChange={(v) => set("parametros_padrao_post", { ...f.parametros_padrao_post, idioma: v })} options={OP_IDIOMA} /></Field>
              <Field label="Formato do artigo"><Select ariaLabel="Formato padrão" value={f.parametros_padrao_artigo.formato} onValueChange={(v) => set("parametros_padrao_artigo", { ...f.parametros_padrao_artigo, formato: v })} options={OP_FORMATO} /></Field>
              <Field label="Público do artigo"><Select ariaLabel="Público padrão" value={f.parametros_padrao_artigo.publico} onValueChange={(v) => set("parametros_padrao_artigo", { ...f.parametros_padrao_artigo, publico: v })} options={OP_PUBLICO} /></Field>
              <Field label="Idioma do artigo"><Select ariaLabel="Idioma padrão do artigo" value={f.parametros_padrao_artigo.idioma} onValueChange={(v) => set("parametros_padrao_artigo", { ...f.parametros_padrao_artigo, idioma: v })} options={OP_IDIOMA} /></Field>
            </div>
          </Card>
          <Card className="flex flex-col gap-4 p-5">
            <h2 className="font-semibold">Execução</h2>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Caminho do Claude Code" htmlFor="cli" hint="Vazio = procurar `claude` no PATH.">
                <Input id="cli" value={f.caminho_cli} onChange={(e) => set("caminho_cli", e.target.value)} placeholder="claude" className="font-mono text-sm" />
              </Field>
              <Field label="Modelo (opcional)" htmlFor="modelo" hint="Vazio = padrão do CLI. Ex.: sonnet, opus.">
                <Input id="modelo" value={f.modelo} onChange={(e) => set("modelo", e.target.value)} className="font-mono text-sm" />
              </Field>
              <Field label="Timeout do post (segundos)" htmlFor="tp">
                <Input id="tp" type="number" min={30} max={3600} value={f.timeout_post_s} onChange={(e) => set("timeout_post_s", Number(e.target.value))} />
              </Field>
              <Field label="Timeout do artigo (segundos)" htmlFor="ta">
                <Input id="ta" type="number" min={30} max={3600} value={f.timeout_artigo_s} onChange={(e) => set("timeout_artigo_s", Number(e.target.value))} />
              </Field>
            </div>
            <Field label="Pasta de dados" htmlFor="pasta" hint="Banco, clones e logs. Alterar exige reiniciar o Shiplog.">
              <Input id="pasta" value={f.pasta_dados} onChange={(e) => set("pasta_dados", e.target.value)} className="font-mono text-sm" />
            </Field>
          </Card>
          {sujo && (
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setF(cfg.data!)}><RotateCcw /> Descartar</Button>
              <Button variant="primary" onClick={() => salvar.mutate(f)} loading={salvar.isPending}><Save /> Salvar</Button>
            </div>
          )}
        </div>
        <div className="flex flex-col gap-6">
          <HealthPanel />
          <Card className="p-5">
            <h2 className="mb-1 font-semibold">Exportar histórico</h2>
            <p className="mb-4 text-sm text-fg-muted">Todos os projetos, versões e status de posts e artigos.</p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => baixar(api.exportUrl("md"))}><Download /> Markdown</Button>
              <Button variant="outline" onClick={() => baixar(api.exportUrl("json"))}><Download /> JSON</Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

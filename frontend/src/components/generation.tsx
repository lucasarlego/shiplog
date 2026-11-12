import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Sparkles, Wand2 } from "lucide-react";
import { toast } from "sonner";
import { api, ApiError } from "@/lib/api";
import type { Health, Job, Projeto, TipoGeracao } from "@/lib/types";
import { modKey } from "@/lib/utils";
import { Button } from "./ui/button";
import { Textarea } from "./ui/input";
import { Card, Field, Switch, Tooltip, Label } from "./ui/misc";
import { Select, type Opcao } from "./ui/select";

export const OP_TOM: Opcao[] = [
  { value: "tecnico", label: "Técnico", desc: "Arquitetura, decisões e trade-offs" },
  { value: "storytelling", label: "Storytelling", desc: "Problema → processo → resultado" },
  { value: "conquista", label: "Conquista / lançamento", desc: "Anuncia o projeto e o valor entregue" },
  { value: "aprendizado", label: "Aprendizado", desc: "Lições práticas e erros" },
];
export const OP_TAMANHO: Opcao[] = [
  { value: "curto", label: "Curto", desc: "500–800 caracteres" },
  { value: "medio", label: "Médio", desc: "900–1.500 caracteres" },
  { value: "longo", label: "Longo", desc: "1.600–2.600 caracteres" },
];
export const OP_IDIOMA: Opcao[] = [
  { value: "pt", label: "Português" },
  { value: "en", label: "Inglês" },
];
export const OP_PUBLICO: Opcao[] = [
  { value: "iniciante", label: "Iniciante" },
  { value: "intermediario", label: "Intermediário" },
  { value: "avancado", label: "Avançado" },
];
export const OP_FORMATO: Opcao[] = [
  { value: "tutorial", label: "Tutorial", desc: "Passo a passo com o código real" },
  { value: "deep_dive", label: "Deep dive", desc: "Um aspecto técnico a fundo" },
  { value: "case_arquitetura", label: "Case de arquitetura", desc: "Problema, desenho e decisões" },
];

export function GenerationPanel({
  projeto,
  tipo,
  health,
  baseVersaoId,
  temVersoes,
  jobAtivo,
  onStarted,
}: {
  projeto: Projeto;
  tipo: TipoGeracao;
  health: Health | undefined;
  baseVersaoId: number | null;
  temVersoes: boolean;
  jobAtivo: boolean;
  onStarted: (j: Job) => void;
}) {
  const qc = useQueryClient();
  const cfg = useQuery({ queryKey: ["settings"], queryFn: api.config });
  const [p, setP] = useState<Record<string, string | boolean>>({});
  const [instrucoes, setInstrucoes] = useState("");
  const [atualizacao, setAtualizacao] = useState(false);
  const [atualizarRepo, setAtualizarRepo] = useState(false);

  useEffect(() => {
    if (cfg.data && !Object.keys(p).length) {
      setP({ ...(tipo === "post" ? cfg.data.parametros_padrao_post : cfg.data.parametros_padrao_artigo) });
    }
  }, [cfg.data, tipo, p]);

  const gerar = useMutation({
    mutationFn: () =>
      api.gerar(projeto.id, {
        tipo,
        parametros: p,
        instrucoes_extras: instrucoes,
        base_versao_id: temVersoes ? baseVersaoId : null,
        atualizacao: tipo === "post" ? atualizacao : false,
        atualizar_repo: tipo === "artigo" ? atualizarRepo : undefined,
      }),
    onSuccess: (j) => {
      setInstrucoes("");
      qc.invalidateQueries({ queryKey: ["jobs", "ativos"] });
      qc.invalidateQueries({ queryKey: ["geracoes", projeto.id] });
      onStarted(j);
    },
    onError: (e: ApiError) => toast.error(e.message, { description: e.erro.acao_sugerida ?? undefined }),
  });

  const pode = tipo === "post" ? health?.pode_gerar_post !== false : health?.pode_gerar_artigo !== false;
  const motivo = !pode
    ? tipo === "artigo" && health?.pode_gerar_post
      ? "Instale a skill medium-article-writer para gerar artigos."
      : "Claude Code indisponível — veja o aviso no topo."
    : jobAtivo
      ? "Já existe uma geração em andamento para este projeto."
      : "";
  const set = (k: string) => (v: string) => setP((o) => ({ ...o, [k]: v }));

  return (
    <Card className="flex flex-col gap-4 p-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Wand2 className="size-4 text-primary" /> {temVersoes ? "Regenerar" : "Gerar"} {tipo === "post" ? "post" : "artigo"}
      </div>
      {tipo === "post" ? (
        <div className="grid grid-cols-1 gap-3">
          <Field label="Tom"><Select ariaLabel="Tom" value={String(p.tom ?? "tecnico")} onValueChange={set("tom")} options={OP_TOM} /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Tamanho"><Select ariaLabel="Tamanho" value={String(p.tamanho ?? "medio")} onValueChange={set("tamanho")} options={OP_TAMANHO} /></Field>
            <Field label="Idioma"><Select ariaLabel="Idioma" value={String(p.idioma ?? "pt")} onValueChange={set("idioma")} options={OP_IDIOMA} /></Field>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          <Field label="Formato"><Select ariaLabel="Formato" value={String(p.formato ?? "deep_dive")} onValueChange={set("formato")} options={OP_FORMATO} /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Público"><Select ariaLabel="Público" value={String(p.publico ?? "intermediario")} onValueChange={set("publico")} options={OP_PUBLICO} /></Field>
            <Field label="Idioma"><Select ariaLabel="Idioma" value={String(p.idioma ?? "pt")} onValueChange={set("idioma")} options={OP_IDIOMA} /></Field>
          </div>
        </div>
      )}
      <Field label="Instruções extras (opcional)" htmlFor={`instr-${tipo}`} hint={temVersoes ? "A versão selecionada vai junto como referência." : undefined}>
        <Textarea
          id={`instr-${tipo}`}
          value={instrucoes}
          onChange={(e) => setInstrucoes(e.target.value)}
          placeholder={tipo === "post" ? "Ex.: menos formal, destaque o uso de Pub/Sub" : "Ex.: foque na fila de jobs e no tratamento de erros"}
          className="min-h-[72px] text-sm"
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && pode && !jobAtivo) {
              e.preventDefault();
              gerar.mutate();
            }
          }}
        />
      </Field>
      {tipo === "post" && projeto.artigo_publicado?.link && (
        <label className="flex items-center justify-between gap-3 text-sm">
          <span>Incluir link do artigo publicado</span>
          <Switch checked={!!p.incluir_link_artigo} onCheckedChange={(v) => setP((o) => ({ ...o, incluir_link_artigo: v }))} />
        </label>
      )}
      {tipo === "post" && projeto.commits_novos && temVersoes && (
        <label className="flex items-center justify-between gap-3 text-sm">
          <span>
            Post de atualização
            <span className="block text-xs text-fg-subtle">Nova rodada sobre os commits novos</span>
          </span>
          <Switch checked={atualizacao} onCheckedChange={setAtualizacao} />
        </label>
      )}
      {tipo === "artigo" && (
        <div className="flex items-center justify-between gap-3 text-sm">
          <Label htmlFor="atualizar-repo" className="text-fg">Atualizar repositório antes</Label>
          <Switch id="atualizar-repo" checked={atualizarRepo} onCheckedChange={setAtualizarRepo} />
        </div>
      )}
      <Tooltip content={motivo || `${modKey()}+Enter`}>
        <span className="w-full">
          <Button variant="primary" className="w-full" onClick={() => gerar.mutate()} loading={gerar.isPending} disabled={!pode || jobAtivo}>
            {temVersoes ? <RefreshCw /> : <Sparkles />}
            {temVersoes ? "Regenerar" : "Gerar"} {tipo === "post" ? "post" : "artigo"}
          </Button>
        </span>
      </Tooltip>
    </Card>
  );
}

import { useState } from "react";
import { motion } from "motion/react";
import { Columns2, Pencil, Sparkles, Terminal } from "lucide-react";
import type { Artigo, Post } from "@/lib/types";
import { cn } from "@/lib/utils";
import { dataHora } from "@/lib/format";
import { StatusBadge, AnimatedCheck } from "./status";
import { Button } from "./ui/button";
import { Dialog } from "./ui/dialog";
import { Input } from "./ui/input";
import { Field } from "./ui/misc";

type V = Post | Artigo;

export function VersionList<T extends V>({
  versoes,
  selecionada,
  onSelect,
  onCompare,
}: {
  versoes: T[];
  selecionada: number | null;
  onSelect: (id: number) => void;
  onCompare: () => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-medium uppercase tracking-wide text-fg-subtle">Versões</span>
        {versoes.length > 1 && (
          <Button size="sm" variant="ghost" onClick={onCompare} className="h-7 px-2">
            <Columns2 /> Comparar
          </Button>
        )}
      </div>
      <div className="flex flex-col gap-1" role="listbox" aria-label="Versões">
        {versoes.map((v) => {
          const sel = v.id === selecionada;
          return (
            <button
              key={v.id}
              role="option"
              aria-selected={sel}
              onClick={() => onSelect(v.id)}
              className={cn(
                "relative flex flex-col items-start gap-1 rounded-md border px-3 py-2 text-left transition-colors duration-fast",
                sel ? "border-grad border shadow-sm" : "border-transparent hover:bg-surface-2",
              )}
            >
              <div className="flex w-full items-center gap-2">
                <span className="font-mono text-sm font-medium">v{v.versao}</span>
                {v.rodada > 1 && <span className="text-xs text-fg-subtle">rodada {v.rodada}</span>}
                <StatusBadge status={v.status} className="ml-auto" />
              </div>
              <div className="flex items-center gap-1 text-xs text-fg-subtle">
                {v.editado_manualmente ? <Pencil className="size-3" /> : v.fonte === "claude_code" ? <Terminal className="size-3" /> : <Sparkles className="size-3" />}
                {v.editado_manualmente ? "Editado" : v.fonte === "claude_code" ? "via Claude Code" : "Gerado"} · {dataHora(v.criado_em)}
              </div>
              {v.instrucoes_extras && !v.editado_manualmente && (
                <div className="line-clamp-1 text-xs italic text-fg-muted">“{v.instrucoes_extras}”</div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function CompareDialog<T extends V>({
  open,
  onOpenChange,
  versoes,
  render,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  versoes: T[];
  render: (v: T) => string;
}) {
  const [a, setA] = useState<number | null>(null);
  const [b, setB] = useState<number | null>(null);
  const va = versoes.find((v) => v.id === a) ?? versoes[1] ?? versoes[0];
  const vb = versoes.find((v) => v.id === b) ?? versoes[0];
  const col = (v: T | undefined, set: (id: number) => void) => (
    <div className="flex min-w-0 flex-1 flex-col gap-2">
      <select
        className="h-8 rounded-md border border-border bg-surface px-2 text-sm"
        value={v?.id}
        onChange={(e) => set(Number(e.target.value))}
        aria-label="Versão"
      >
        {versoes.map((x) => (
          <option key={x.id} value={x.id}>
            v{x.versao} — {x.editado_manualmente ? "editado" : "gerado"} — {x.status}
          </option>
        ))}
      </select>
      <div className="h-[60vh] overflow-auto rounded-md border border-border bg-surface-2 p-4 text-sm leading-relaxed whitespace-pre-wrap">
        {v ? render(v) : ""}
      </div>
    </div>
  );
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Comparar versões" className="w-[min(96vw,1100px)]">
      <div className="flex gap-4">
        {col(va, setA)}
        {col(vb, setB)}
      </div>
    </Dialog>
  );
}

export function PublishDialog({
  open,
  onOpenChange,
  plataforma,
  linkInicial,
  onConfirm,
  loading,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  plataforma: "LinkedIn" | "Medium";
  linkInicial: string | null;
  onConfirm: (link: string) => Promise<void>;
  loading: boolean;
}) {
  const [link, setLink] = useState(linkInicial ?? "");
  const [feito, setFeito] = useState(false);
  const [erro, setErro] = useState("");
  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        onOpenChange(o);
        if (!o) setTimeout(() => setFeito(false), 300);
      }}
      title={feito ? "Marcado como publicado" : "Marcar como publicado"}
      description={feito ? undefined : `Você publica manualmente no ${plataforma}. Cole o link para guardar no histórico (opcional).`}
    >
      {feito ? (
        <motion.div className="flex flex-col items-center gap-3 py-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <AnimatedCheck />
          <p className="text-sm text-fg-muted">Registrado no histórico.</p>
          <Button onClick={() => onOpenChange(false)}>Fechar</Button>
        </motion.div>
      ) : (
        <form
          className="flex flex-col gap-4"
          onSubmit={async (e) => {
            e.preventDefault();
            if (link && !/^https?:\/\//.test(link)) {
              setErro("O link deve começar com https://");
              return;
            }
            try {
              await onConfirm(link);
              setFeito(true);
            } catch (err) {
              setErro((err as Error).message);
            }
          }}
        >
          <Field label={`Link do post no ${plataforma}`} htmlFor="link-pub">
            <Input
              id="link-pub"
              value={link}
              onChange={(e) => {
                setLink(e.target.value);
                setErro("");
              }}
              placeholder={plataforma === "LinkedIn" ? "https://www.linkedin.com/posts/..." : "https://medium.com/@voce/..."}
              aria-invalid={!!erro}
              autoFocus
            />
          </Field>
          {erro && <p className="text-sm text-st-erro" role="alert">{erro}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button type="submit" variant="primary" loading={loading}>Marcar como publicado</Button>
          </div>
        </form>
      )}
    </Dialog>
  );
}

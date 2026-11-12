import { useState, type ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { Command } from "cmdk";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Copy, FolderGit2, LayoutGrid, Monitor, Moon, RefreshCw, Search, Settings, Sun, Terminal, ClipboardPaste, PenLine, MessageSquareText } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useTheme, type Tema } from "@/lib/theme";
import { emCampoDeTexto, mod, runCopyTarget, useHealth, useHotkey } from "@/lib/hooks";
import { cn, modKey } from "@/lib/utils";
import { dur, ease } from "@/lib/motion";
import { Button } from "./ui/button";
import { Kbd, Tooltip } from "./ui/misc";

export function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight">
      <img src="/favicon.svg" alt="" className="size-6" />
      Shiplog
    </Link>
  );
}

export function ThemeToggle() {
  const { tema, setTema } = useTheme();
  const opcoes: { v: Tema; icon: typeof Sun; label: string }[] = [
    { v: "claro", icon: Sun, label: "Tema claro" },
    { v: "escuro", icon: Moon, label: "Tema escuro" },
    { v: "sistema", icon: Monitor, label: "Seguir o sistema" },
  ];
  return (
    <div className="flex items-center rounded-md bg-surface-2 p-0.5" role="radiogroup" aria-label="Tema">
      {opcoes.map(({ v, icon: Icon, label }) => (
        <Tooltip key={v} content={label} side="bottom">
          <button
            role="radio"
            aria-checked={tema === v}
            aria-label={label}
            onClick={() => setTema(v)}
            className={cn(
              "flex size-7 items-center justify-center rounded-sm text-fg-subtle transition-colors duration-fast hover:text-fg",
              tema === v && "bg-surface text-fg shadow-sm",
            )}
          >
            <Icon className="size-3.5" />
          </button>
        </Tooltip>
      ))}
    </div>
  );
}

/** Aviso persistente se o Claude Code não estiver pronto (RI-07, RI-09). */
export function HealthBanner() {
  const { data } = useHealth();
  const qc = useQueryClient();
  const [checando, setChecando] = useState(false);
  if (!data) return null;
  const problemas: { msg: string; cmd?: string | null }[] = [];
  if (!data.cli.ok) problemas.push({ msg: data.cli.mensagem ?? "Claude Code indisponível.", cmd: data.cli.comando_sugerido });
  else if (!data.auth.ok) problemas.push({ msg: data.auth.mensagem ?? "Claude Code não autenticado.", cmd: data.auth.comando_sugerido });
  if (!data.git.ok) problemas.push({ msg: data.git.mensagem ?? "git não encontrado." });
  if (!data.skill.ok) problemas.push({ msg: data.skill.mensagem ?? "Skill ausente.", cmd: data.skill.comando_sugerido });
  if (!problemas.length) return null;
  const grave = !data.pode_gerar_post;
  return (
    <div className={cn("border-b px-6 py-2.5", grave ? "border-st-erro/30 bg-st-erro-soft" : "border-st-novos/30 bg-st-novos-soft")} role="alert">
      <div className="mx-auto flex max-w-[88rem] items-start gap-3">
        <AlertTriangle className={cn("mt-0.5 size-4 shrink-0", grave ? "text-st-erro" : "text-st-novos")} />
        <div className="flex-1 space-y-1 text-sm">
          {problemas.map((p) => (
            <div key={p.msg}>
              <span className="font-medium">{p.msg}</span>
              {p.cmd && (
                <span className="ml-2 text-fg-muted">
                  <Terminal className="mr-1 inline size-3.5" />
                  {p.cmd}
                </span>
              )}
            </div>
          ))}
        </div>
        <Button
          size="sm"
          variant="ghost"
          loading={checando}
          onClick={async () => {
            setChecando(true);
            try {
              qc.setQueryData(["health"], await api.healthRefresh());
            } finally {
              setChecando(false);
            }
          }}
        >
          <RefreshCw /> Verificar de novo
        </Button>
      </div>
    </div>
  );
}

function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const navigate = useNavigate();
  const { setTema } = useTheme();
  const projetos = useQuery({ queryKey: ["projects", ""], queryFn: () => api.projetos(), enabled: open });
  const run = (fn: () => void) => {
    onOpenChange(false);
    setTimeout(fn, 0);
  };
  const item =
    "flex cursor-default items-center gap-2.5 rounded-md px-3 py-2 text-base text-fg-muted data-[selected=true]:bg-surface-2 data-[selected=true]:text-fg [&_svg]:size-4";
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-start justify-center bg-overlay pt-[14vh] backdrop-blur-[2px]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: dur.fast }}
          onMouseDown={(e) => e.target === e.currentTarget && onOpenChange(false)}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.98, y: -6 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: dur.base, ease: ease.out }}
            className="w-[min(92vw,580px)] overflow-hidden rounded-xl border border-border bg-surface shadow-lg"
          >
            <Command label="Paleta de comandos" loop onKeyDown={(e) => e.key === "Escape" && onOpenChange(false)}>
              <div className="flex items-center gap-2 border-b border-border px-4">
                <Search className="size-4 text-fg-subtle" />
                <Command.Input autoFocus placeholder="Buscar projetos e ações…" className="h-12 flex-1 bg-transparent text-md outline-none placeholder:text-fg-subtle" />
                <Kbd>Esc</Kbd>
              </div>
              <Command.List className="max-h-[50vh] overflow-y-auto p-2">
                <Command.Empty className="px-3 py-6 text-center text-sm text-fg-subtle">Nada encontrado.</Command.Empty>
                <Command.Group heading="Ações" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-fg-subtle">
                  <Command.Item className={item} onSelect={() => run(() => navigate("/?modo=repo"))}>
                    <FolderGit2 /> Nova geração a partir de URL
                  </Command.Item>
                  <Command.Item className={item} onSelect={() => run(() => navigate("/?modo=descrever"))}>
                    <PenLine /> Novo post a partir de uma descrição
                  </Command.Item>
                  <Command.Item className={item} onSelect={() => run(() => navigate("/comentarios"))}>
                    <MessageSquareText /> Novo comentário em post de outra pessoa
                  </Command.Item>
                  <Command.Item
                    className={item}
                    onSelect={() =>
                      run(async () => {
                        try {
                          const txt = await navigator.clipboard.readText();
                          navigate(`/?url=${encodeURIComponent(txt.trim())}`);
                        } catch {
                          toast.error("O navegador bloqueou a leitura da área de transferência.");
                        }
                      })
                    }
                  >
                    <ClipboardPaste /> Colar URL da área de transferência e gerar
                  </Command.Item>
                  <Command.Item className={item} onSelect={() => run(() => { if (!runCopyTarget()) toast("Abra um post ou artigo para copiar."); })}>
                    <Copy /> Copiar texto atual
                  </Command.Item>
                  <Command.Item className={item} onSelect={() => run(() => navigate("/"))}>
                    <LayoutGrid /> Ir para o painel
                  </Command.Item>
                  <Command.Item className={item} onSelect={() => run(() => navigate("/configuracoes"))}>
                    <Settings /> Configurações
                  </Command.Item>
                  <Command.Item className={item} onSelect={() => run(() => setTema("claro"))}>
                    <Sun /> Tema claro
                  </Command.Item>
                  <Command.Item className={item} onSelect={() => run(() => setTema("escuro"))}>
                    <Moon /> Tema escuro
                  </Command.Item>
                </Command.Group>
                {!!projetos.data?.length && (
                  <Command.Group heading="Projetos" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-fg-subtle">
                    {projetos.data.map((p) => (
                      <Command.Item key={p.id} value={`${p.id} ${p.nome} ${p.url_repo ?? p.descricao.slice(0, 80)}`} className={item} onSelect={() => run(() => navigate(`/projetos/${p.id}`))}>
                        {p.origem === "livre" ? <PenLine /> : <FolderGit2 />} {p.nome}
                        <span className="ml-auto truncate text-xs text-fg-subtle">{p.url_repo ?? "Sem repositório"}</span>
                      </Command.Item>
                    ))}
                  </Command.Group>
                )}
              </Command.List>
            </Command>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [paleta, setPaleta] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  // Atalhos globais (RUI-15)
  useHotkey((e) => mod(e) && e.key.toLowerCase() === "k", (e) => { e.preventDefault(); setPaleta((o) => !o); });
  useHotkey((e) => mod(e) && e.shiftKey && e.key.toLowerCase() === "c", (e) => {
    if (runCopyTarget()) e.preventDefault();
  });
  useHotkey((e) => e.key === "/" && !emCampoDeTexto(e) && !mod(e), (e) => {
    e.preventDefault();
    if (location.pathname !== "/") navigate("/");
    setTimeout(() => (document.getElementById("url-input") ?? document.getElementById("descricao-input"))?.focus(), 50);
  });

  const nav = "flex h-8 items-center gap-1.5 rounded-md px-3 text-sm font-medium text-fg-muted transition-colors duration-fast hover:text-fg hover:bg-surface-2 [&.active]:text-fg [&.active]:bg-surface-2 [&_svg]:size-4";
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-border bg-bg/80 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-[88rem] items-center gap-6 px-6">
          <Logo />
          <nav className="flex items-center gap-1">
            <NavLink to="/" end className={nav}><LayoutGrid /> Painel</NavLink>
            <NavLink to="/comentarios" className={nav}><MessageSquareText /> Comentários</NavLink>
            <NavLink to="/configuracoes" className={nav}><Settings /> Configurações</NavLink>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => setPaleta(true)}
              className="flex h-8 items-center gap-2 rounded-md border border-border bg-surface px-3 text-sm text-fg-subtle shadow-sm transition-colors duration-fast hover:border-border-strong hover:text-fg-muted"
            >
              <Search className="size-3.5" /> Buscar ou executar…
              <span className="ml-4 flex gap-0.5"><Kbd>{modKey()}</Kbd><Kbd>K</Kbd></span>
            </button>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <HealthBanner />
      <AnimatePresence mode="wait">
        <motion.main
          key={location.pathname}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: dur.base, ease: ease.out }}
          className="mx-auto max-w-[88rem] px-6 py-8"
        >
          {children}
        </motion.main>
      </AnimatePresence>
      <CommandPalette open={paleta} onOpenChange={setPaleta} />
    </div>
  );
}

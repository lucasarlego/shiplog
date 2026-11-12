import { motion, useReducedMotion } from "motion/react";
import { CheckCircle2, CircleDashed, CircleDot, GitCommitHorizontal, AlertTriangle, Send } from "lucide-react";
import type { StatusVersao } from "@/lib/types";
import { cn } from "@/lib/utils";
import { dur, ease } from "@/lib/motion";

// Cores de status fixas e sempre com ícone + rótulo (RUI-03).
const STATUS = {
  rascunho: { label: "Rascunho", icon: CircleDashed, cls: "bg-st-rascunho-soft text-st-rascunho" },
  pronto: { label: "Pronto", icon: CircleDot, cls: "bg-st-pronto-soft text-st-pronto" },
  publicado: { label: "Publicado", icon: CheckCircle2, cls: "bg-st-publicado-soft text-st-publicado" },
} as const;

export function StatusBadge({ status, className }: { status: StatusVersao | null | undefined; className?: string }) {
  if (!status) {
    return (
      <span className={cn("inline-flex items-center gap-1 rounded-full bg-surface-2 px-2 py-0.5 text-xs font-medium text-fg-subtle", className)}>
        <Send className="size-3" /> Sem post
      </span>
    );
  }
  const s = STATUS[status];
  const Icon = s.icon;
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium", s.cls, className)}>
      <Icon className="size-3" />
      {s.label}
    </span>
  );
}

export function NewCommitsBadge({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full bg-st-novos-soft px-2 py-0.5 text-xs font-medium text-st-novos", className)}>
      <GitCommitHorizontal className="size-3" /> Commits novos
    </span>
  );
}

export function ErrorBadge({ label = "Erro" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-st-erro-soft px-2 py-0.5 text-xs font-medium text-st-erro">
      <AlertTriangle className="size-3" /> {label}
    </span>
  );
}

/** Check desenhado ao marcar como publicado (RUI-11). */
export function AnimatedCheck({ size = 56 }: { size?: number }) {
  const reduce = useReducedMotion();
  return (
    <motion.svg
      width={size}
      height={size}
      viewBox="0 0 52 52"
      initial={{ opacity: 0, scale: reduce ? 1 : 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: dur.slow, ease: ease.out }}
      className="text-st-publicado"
      aria-hidden
    >
      <circle cx="26" cy="26" r="24" fill="var(--st-publicado-soft)" />
      <motion.path
        d="M15 27l7 7 15-16"
        fill="none"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: reduce ? 1 : 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: dur.slower, ease: ease.out, delay: reduce ? 0 : 0.1 }}
      />
    </motion.svg>
  );
}

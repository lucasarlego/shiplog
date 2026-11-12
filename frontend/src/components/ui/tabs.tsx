import * as TabsPrimitive from "@radix-ui/react-tabs";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { dur, ease } from "@/lib/motion";

export const Tabs = TabsPrimitive.Root;
export const TabsContent = TabsPrimitive.Content;

/** Lista de abas com indicador deslizante (layoutId). */
export function TabsList({
  items,
  value,
  layoutId,
  className,
}: {
  items: { value: string; label: ReactNode; icon?: ReactNode; badge?: ReactNode; disabled?: boolean; hint?: string }[];
  value: string;
  layoutId: string;
  className?: string;
}) {
  return (
    <TabsPrimitive.List className={cn("inline-flex items-center gap-1 rounded-lg bg-surface-2 p-1", className)}>
      {items.map((it) => (
        <TabsPrimitive.Trigger
          key={it.value}
          value={it.value}
          disabled={it.disabled}
          title={it.hint}
          className={cn(
            "relative inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-sm font-medium text-fg-muted transition-colors duration-fast",
            "hover:text-fg data-[state=active]:text-fg [&_svg]:size-4",
            "disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:text-fg-muted",
          )}
        >
          {value === it.value && (
            <motion.span
              layoutId={layoutId}
              className="absolute inset-0 rounded-md bg-surface shadow-sm"
              transition={{ duration: dur.base, ease: ease.out }}
            />
          )}
          <span className="relative z-10 inline-flex items-center gap-1.5">
            {it.icon}
            {it.label}
            {it.badge}
          </span>
        </TabsPrimitive.Trigger>
      ))}
    </TabsPrimitive.List>
  );
}

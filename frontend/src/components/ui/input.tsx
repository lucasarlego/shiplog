import { forwardRef, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const base =
  "w-full bg-surface border border-border rounded-md text-fg placeholder:text-fg-subtle shadow-sm " +
  "transition-[border-color,box-shadow] duration-fast ease-out " +
  "hover:border-border-strong focus:outline-none focus:border-primary focus:ring-3 focus:ring-primary/20 " +
  "disabled:opacity-60 aria-invalid:border-st-erro aria-invalid:ring-st-erro/20";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(({ className, ...p }, ref) => (
  <input ref={ref} className={cn(base, "h-9 px-3 text-base", className)} {...p} />
));
Input.displayName = "Input";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...p }, ref) => (
    <textarea ref={ref} className={cn(base, "px-3 py-2.5 text-base leading-relaxed resize-y", className)} {...p} />
  ),
);
Textarea.displayName = "Textarea";

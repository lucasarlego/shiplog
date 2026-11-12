import { Slot } from "@radix-ui/react-slot";
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "secondary" | "ghost" | "outline" | "danger" | "soft";
type Size = "sm" | "md" | "lg" | "icon" | "icon-sm";

const variants: Record<Variant, string> = {
  primary:
    "bg-grad-primary text-white shadow-glow hover:brightness-110 active:brightness-95 disabled:shadow-none",
  secondary: "bg-fg text-bg hover:opacity-90",
  soft: "bg-primary-soft text-primary-soft-fg hover:brightness-[0.97] dark:hover:brightness-110",
  outline: "border border-border bg-surface text-fg hover:bg-surface-2 hover:border-border-strong shadow-sm",
  ghost: "text-fg-muted hover:text-fg hover:bg-surface-2",
  danger: "bg-st-erro text-white hover:brightness-110",
};
const sizes: Record<Size, string> = {
  sm: "h-8 px-3 text-sm gap-1.5 rounded-md",
  md: "h-9 px-4 text-sm gap-2 rounded-md",
  lg: "h-11 px-5 text-md gap-2 rounded-lg",
  icon: "h-9 w-9 rounded-md",
  "icon-sm": "h-7 w-7 rounded-sm",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  asChild?: boolean;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "outline", size = "md", asChild, loading, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap font-medium select-none",
          "transition-[background-color,border-color,color,filter,box-shadow,transform] duration-fast ease-out",
          "active:scale-[0.97] motion-reduce:active:scale-100",
          "disabled:opacity-50 disabled:pointer-events-none",
          "[&_svg]:size-4 [&_svg]:shrink-0",
          variants[variant],
          sizes[size],
          className,
        )}
        {...props}
      >
        {asChild ? (
          children
        ) : (
          <>
            {loading && <Loader2 className="animate-spin motion-reduce:animate-none" />}
            {children}
          </>
        )}
      </Comp>
    );
  },
);
Button.displayName = "Button";

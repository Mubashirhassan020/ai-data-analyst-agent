import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Tone = "neutral" | "success" | "warning" | "danger" | "info" | "accent";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-border/50 text-fg",
  success: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30",
  warning: "bg-amber-500/10 text-amber-400 border border-amber-500/30",
  danger: "bg-red-500/10 text-red-400 border border-red-500/30",
  info: "bg-sky-500/10 text-sky-400 border border-sky-500/30",
  accent: "bg-accent/10 text-accent border border-accent/30",
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

export function Badge({ className, tone = "neutral", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
        toneClasses[tone],
        className
      )}
      {...props}
    />
  );
}

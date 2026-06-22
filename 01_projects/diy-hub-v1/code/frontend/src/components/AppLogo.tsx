import { cn } from "@/lib/utils"

export function AppLogo({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "flex h-24 w-28 shrink-0 items-center justify-center rounded-lg border border-slate-900/10 bg-white shadow-[0_14px_34px_rgba(15,23,42,0.18)] dark:border-teal-300/50 dark:bg-slate-950 dark:p-2 dark:shadow-[0_0_0_1px_rgba(45,212,191,0.24),0_0_28px_rgba(20,184,166,0.22),0_22px_50px_rgba(0,0,0,0.55)]",
        className,
      )}
    >
      <span className="flex h-full w-full items-center justify-center rounded-md bg-white ring-1 ring-slate-900/10 dark:ring-white/20">
        <img
          src="/brand/diy-hub-option-6-logo-centered.png"
          alt="DIY HUB CODEX V2"
          className="h-20 w-20 object-contain"
        />
      </span>
    </span>
  )
}

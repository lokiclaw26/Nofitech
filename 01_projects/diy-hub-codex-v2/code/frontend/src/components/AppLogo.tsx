import { cn } from "@/lib/utils"

export function AppLogo({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "flex h-16 w-20 shrink-0 items-center justify-center rounded-lg border border-slate-900/10 bg-white shadow-[0_10px_24px_rgba(15,23,42,0.12)] dark:border-white/15 dark:bg-white",
        className,
      )}
    >
      <img
        src="/brand/diy-hub-option-6-logo-centered.png"
        alt="DIY HUB CODEX V2"
        className="h-14 w-14 object-contain"
      />
    </span>
  )
}

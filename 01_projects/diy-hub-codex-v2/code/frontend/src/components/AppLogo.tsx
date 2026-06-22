import { cn } from "@/lib/utils"

export function AppLogo({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "flex h-12 w-16 shrink-0 items-center justify-center overflow-hidden rounded-md",
        className,
      )}
    >
      <img
        src="/brand/diy-hub-option-6-logo-centered.png"
        alt="DIY HUB CODEX V2"
        className="h-12 w-12 object-contain"
      />
    </span>
  )
}

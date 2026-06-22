import { cn } from "@/lib/utils"

export function AppLogo({ className }: { className?: string }) {
  return (
    <img
      src="/brand/diy-hub-option-6-logo.png"
      alt="DIY HUB CODEX V2"
      className={cn(
        "h-12 w-auto shrink-0 rounded-md object-contain",
        className,
      )}
    />
  )
}

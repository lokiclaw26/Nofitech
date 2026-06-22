import { cn } from "@/lib/utils"

export function AppLogo({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "relative flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-slate-950 text-white shadow-[0_10px_24px_rgba(15,23,42,0.26)] dark:bg-white dark:text-slate-950",
        className,
      )}
      aria-hidden="true"
    >
      <svg viewBox="0 0 44 44" className="h-9 w-9 overflow-visible" fill="none">
        <g>
          <rect x="8" y="19" width="24" height="15" rx="3" fill="currentColor" opacity="0.14" />
          <rect x="10" y="21" width="20" height="4" rx="1.5" fill="#14b8a6" />
          <rect x="10" y="27" width="20" height="5" rx="1.5" fill="currentColor" opacity="0.9" />
          <path d="M14 29.5h4M22 29.5h4" stroke="#fbbf24" strokeWidth="1.6" strokeLinecap="round" />
          <path d="M12 17h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.74" />
          <path d="M13 14.5h3m4 0h3m4 0h3" stroke="#38bdf8" strokeWidth="1.5" strokeLinecap="round" />
        </g>

        <g>
          <circle cx="27" cy="15" r="6.5" stroke="#f8fafc" strokeWidth="2.4" className="dark:stroke-slate-950" />
          <circle cx="27" cy="15" r="3" fill="#14b8a6" opacity="0.22" />
          <path d="M31.5 20l5.2 5.2" stroke="#fbbf24" strokeWidth="3" strokeLinecap="round" />
        </g>

        <path
          d="M7 36c6.5 2.5 22.5 2.5 29 0"
          stroke="#14b8a6"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      </svg>
    </div>
  )
}

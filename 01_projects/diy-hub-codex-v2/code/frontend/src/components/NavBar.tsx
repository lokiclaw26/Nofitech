import { NavLink } from "react-router-dom"
import { Boxes, LayoutDashboard, Lightbulb, Moon, Plus, Settings, Sun, Zap } from "lucide-react"
import { AppLogo } from "@/components/AppLogo"
import { cn } from "@/lib/utils"

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/inventory", label: "Inventory", icon: Boxes },
  { to: "/add", label: "Add", icon: Plus },
  { to: "/ideas", label: "Idea Lab", icon: Lightbulb },
  { to: "/settings", label: "Settings", icon: Settings },
]

export function NavBar({
  darkMode,
  onToggleDarkMode,
}: {
  darkMode: boolean
  onToggleDarkMode: () => void
}) {
  return (
    <nav className="sticky top-0 z-40 border-b border-slate-900/10 bg-[#f8f8f1]/90 backdrop-blur-xl transition-colors duration-500 dark:border-white/10 dark:bg-slate-950/80">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-2">
        <NavLink to="/" className="flex min-w-0 items-center pr-2">
          <AppLogo />
        </NavLink>
        <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
          {links.map((link) => {
            const Icon = link.icon
            return (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "group inline-flex h-10 shrink-0 items-center gap-2 rounded-md px-3 text-sm font-semibold transition",
                    isActive
                      ? "bg-slate-950 text-white shadow-[0_10px_24px_rgba(15,23,42,0.2)]"
                      : "text-slate-600 hover:-translate-y-0.5 hover:bg-white hover:text-slate-950 hover:shadow-sm dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white",
                  )
                }
                title={link.label}
              >
                <Icon className="h-4 w-4 transition group-hover:rotate-[-6deg]" />
                <span className="hidden sm:inline">{link.label}</span>
              </NavLink>
            )
          })}
        </div>
        <span className="hidden items-center gap-1.5 rounded-md border border-teal-200 bg-teal-50 px-2.5 py-1 text-xs font-bold text-teal-800 md:inline-flex">
          <Zap className="h-3.5 w-3.5" />
          Live workshop
        </span>
        <button
          type="button"
          onClick={onToggleDarkMode}
          className="group relative flex h-10 w-16 shrink-0 items-center rounded-full border border-slate-900/10 bg-white p-1 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-white/10 dark:bg-slate-900"
          title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
          aria-label={darkMode ? "Switch to light mode" : "Switch to dark mode"}
          aria-pressed={darkMode}
        >
          <span
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-full bg-slate-950 text-white shadow-md transition duration-300 group-hover:rotate-12 dark:bg-amber-300 dark:text-slate-950",
              darkMode && "translate-x-6",
            )}
          >
            {darkMode ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
          </span>
        </button>
      </div>
    </nav>
  )
}

import { NavLink } from "react-router-dom"
import { Boxes, Cpu, LayoutDashboard, Lightbulb, Plus, Settings } from "lucide-react"
import { cn } from "@/lib/utils"

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/inventory", label: "Inventory", icon: Boxes },
  { to: "/add", label: "Add", icon: Plus },
  { to: "/ideas", label: "Idea Lab", icon: Lightbulb },
  { to: "/settings", label: "Settings", icon: Settings },
]

export function NavBar() {
  return (
    <nav className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3">
        <NavLink to="/" className="flex min-w-0 items-center gap-2 pr-2">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-slate-950 text-white">
            <Cpu className="h-5 w-5" />
          </span>
          <span className="hidden font-semibold text-slate-950 sm:inline">DIY Hub</span>
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
                    "inline-flex h-9 shrink-0 items-center gap-2 rounded-md px-3 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-slate-950 text-white"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-950",
                  )
                }
                title={link.label}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{link.label}</span>
              </NavLink>
            )
          })}
        </div>
        <span className="hidden rounded-md bg-teal-50 px-2.5 py-1 text-xs font-medium text-teal-700 md:inline">
          Personal workshop
        </span>
      </div>
    </nav>
  )
}

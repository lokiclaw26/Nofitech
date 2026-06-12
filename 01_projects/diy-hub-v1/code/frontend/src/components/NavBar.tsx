import { NavLink } from "react-router-dom"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/add", label: "Add Component" },
  { to: "/inventory", label: "Inventory" },
  { to: "/ideas", label: "Idea Lab" },
  { to: "/settings", label: "Settings" },
]

export function NavBar() {
  return (
    <motion.nav
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="bg-slate-900 text-white border-b border-slate-800"
    >
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-3 flex-wrap">
        <span className="font-semibold text-lg mr-4">DIY Hub</span>
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) =>
              cn(
                "px-3 py-1.5 rounded-md text-sm transition-colors",
                isActive
                  ? "bg-slate-700 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              )
            }
          >
            {link.label}
          </NavLink>
        ))}
        <div className="ml-auto">
          <Button variant="secondary" size="sm" disabled>
            v0.1.0 — Stage 1
          </Button>
        </div>
      </div>
    </motion.nav>
  )
}

import { useEffect, useState } from "react"
import { BrowserRouter, Routes, Route } from "react-router-dom"
import { NavBar } from "@/components/NavBar"
import Dashboard from "@/pages/Dashboard"
import AddComponent from "@/pages/AddComponent"
import Inventory from "@/pages/Inventory"
import IdeaLab from "@/pages/IdeaLab"
import BuildStudio from "@/pages/BuildStudio"
import Settings from "@/pages/Settings"

function App() {
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem("diyhub-theme") === "dark")

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode)
    localStorage.setItem("diyhub-theme", darkMode ? "dark" : "light")
  }, [darkMode])

  return (
    <BrowserRouter>
      <main className="min-h-screen bg-[#f6f7ef] text-slate-950 transition-colors duration-500 dark:bg-slate-950 dark:text-slate-100">
        <div className="fixed inset-0 -z-10 bg-workbench" />
        <div className="pointer-events-none fixed inset-x-0 top-0 -z-10 h-28 animate-scanline bg-gradient-to-b from-teal-400/12 to-transparent dark:from-teal-300/12" />
        <NavBar darkMode={darkMode} onToggleDarkMode={() => setDarkMode((current) => !current)} />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/add" element={<AddComponent />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/ideas" element={<IdeaLab />} />
          <Route path="/build" element={<BuildStudio />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App

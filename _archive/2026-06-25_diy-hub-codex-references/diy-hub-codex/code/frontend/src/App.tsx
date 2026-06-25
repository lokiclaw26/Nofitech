import { BrowserRouter, Routes, Route } from "react-router-dom"
import { NavBar } from "@/components/NavBar"
import Dashboard from "@/pages/Dashboard"
import AddComponent from "@/pages/AddComponent"
import Inventory from "@/pages/Inventory"
import IdeaLab from "@/pages/IdeaLab"
import Settings from "@/pages/Settings"

function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <main className="min-h-screen bg-slate-50 text-slate-900">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/add" element={<AddComponent />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/ideas" element={<IdeaLab />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App

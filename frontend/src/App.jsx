import React from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'

export default function App(){
  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <nav className="px-6 py-4 flex items-center justify-between">
          <div className="text-xl font-semibold">InsiderGuard</div>
          <div className="space-x-4">
            <Link to="/" className="text-sm text-slate-300">Home</Link>
            <Link to="/dashboard" className="text-sm text-slate-300">Dashboard</Link>
          </div>
        </nav>

        <Routes>
          <Route path="/" element={<Landing/>} />
          <Route path="/dashboard" element={<Dashboard/>} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

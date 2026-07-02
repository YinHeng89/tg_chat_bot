import { useState, useCallback } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './components/Login'
import Dashboard from './pages/Dashboard'
import Bots from './pages/Bots'
import ModelConfig from './pages/ModelConfig'
import Connectors from './pages/Connectors'
import Blacklist from './pages/Blacklist'
import Sessions from './pages/Sessions'
import Diagnostics from './pages/Diagnostics'

function App() {
  const [token, setToken] = useState(localStorage.getItem('admin_token') || '')

  const handleLogin = useCallback((newToken) => {
    localStorage.setItem('admin_token', newToken)
    setToken(newToken)
  }, [])

  const handleLogout = useCallback(() => {
    localStorage.removeItem('admin_token')
    setToken('')
  }, [])

  if (!token) return <Login onLogin={handleLogin} />

  return (
    <BrowserRouter>
      <Layout token={token} onLogout={handleLogout}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/bots" element={<Bots />} />
          <Route path="/models" element={<ModelConfig />} />
          <Route path="/connectors" element={<Connectors />} />
          <Route path="/blacklist" element={<Blacklist />} />
          <Route path="/sessions" element={<Sessions />} />
          <Route path="/diagnostics" element={<Diagnostics />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App

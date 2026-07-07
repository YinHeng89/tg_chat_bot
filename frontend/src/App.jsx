import { useState, useCallback, useEffect, createContext, useContext } from 'react'
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
import Tasks from './pages/Tasks'

// ===== 主题 Context =====
export const ThemeContext = createContext()
export function useTheme() { return useContext(ThemeContext) }

function getInitialTheme() {
  const stored = localStorage.getItem('theme')
  if (stored === 'light' || stored === 'dark') return stored
  return null // null = 跟随系统
}

function App() {
  const [token, setToken] = useState(localStorage.getItem('admin_token') || '')
  const [theme, setThemeState] = useState(getInitialTheme)

  const setTheme = useCallback((t) => {
    setThemeState(t)
    if (t) {
      localStorage.setItem('theme', t)
      document.documentElement.setAttribute('data-theme', t)
    } else {
      localStorage.removeItem('theme')
      document.documentElement.removeAttribute('data-theme')
    }
  }, [])

  // 初始化 & 监听系统偏好变化
  useEffect(() => {
    if (theme) {
      document.documentElement.setAttribute('data-theme', theme)
    }
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => {
      if (!localStorage.getItem('theme')) {
        document.documentElement.removeAttribute('data-theme')
      }
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [theme])

  const cycleTheme = useCallback(() => {
    const order = [null, 'light', 'dark'] // null=系统, light, dark 三态循环
    const idx = order.indexOf(theme)
    setTheme(order[(idx + 1) % order.length])
  }, [theme, setTheme])

  const themeLabel = theme === null ? '跟随系统' : theme === 'light' ? '亮色' : '暗色'

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
      <ThemeContext.Provider value={{ theme, setTheme, cycleTheme, themeLabel }}>
        <Layout token={token} onLogout={handleLogout}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/bots" element={<Bots />} />
            <Route path="/models" element={<ModelConfig />} />
            <Route path="/connectors" element={<Connectors />} />
            <Route path="/blacklist" element={<Blacklist />} />
            <Route path="/sessions" element={<Sessions />} />
            <Route path="/diagnostics" element={<Diagnostics />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </ThemeContext.Provider>
    </BrowserRouter>
  )
}

export default App

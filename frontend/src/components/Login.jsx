import { useState } from 'react'
import { login } from '../api'

export default function Login({ onLogin }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!password) return
    setError('')
    setLoading(true)
    try {
      const data = await login(password)
      onLogin(data.access_token)
    } catch (err) {
      setError(err.message || '密码错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        {/* Logo */}
        <div className="login-logo">
          <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="48" height="48" rx="12" fill="url(#loginGrad)"/>
            <path d="M14 18a4 4 0 014-4h12a4 4 0 014 4v2a4 4 0 01-4 4h-8l-4 4v-4a4 4 0 01-4-4v-2z" fill="white"/>
            <circle cx="21" cy="22" r="1.5" fill="#6366f1"/>
            <circle cx="27" cy="22" r="1.5" fill="#6366f1"/>
            <defs>
              <linearGradient id="loginGrad" x1="0" y1="0" x2="48" y2="48">
                <stop offset="0%" stopColor="#6366f1"/>
                <stop offset="100%" stopColor="#8b5cf6"/>
              </linearGradient>
            </defs>
          </svg>
        </div>

        <h1>TG Chat Bot</h1>
        <p className="login-subtitle">Telegram Bot 管理面板</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>管理密码</label>
            <div className="login-input-wrap">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" width="18" height="18" className="login-input-icon">
                <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>
                <circle cx="12" cy="16" r="1"/>
              </svg>
              <input
                type="password"
                value={password}
                onChange={e => { setPassword(e.target.value); setError('') }}
                placeholder="请输入管理密码"
                autoFocus
              />
            </div>
          </div>

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className={`login-btn ${loading ? 'loading' : ''}`} disabled={loading}>
            {loading ? (
              <span className="spinner"/>
            ) : '登录'}
          </button>
        </form>
      </div>
    </div>
  )
}

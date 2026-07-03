import { useState, useEffect } from 'react'
import { login, checkSetup, setupPassword, resetPassword } from '../api'

export default function Login({ onLogin }) {
  // 流程状态: 'loading' | 'setup' | 'login' | 'reset' | 'show_recovery' | 'done_setup'
  const [step, setStep] = useState('loading')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [recoveryCode, setRecoveryCode] = useState('')
  const [displayRecoveryCode, setDisplayRecoveryCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    checkSetup()
      .then(d => setStep(d.need_setup ? 'setup' : 'login'))
      .catch(() => setStep('login'))  // fallback
  }, [])

  // ===== 首次设置 =====
  const handleSetup = async (e) => {
    e.preventDefault()
    setError('')
    if (!password) { setError('请输入密码'); return }
    if (password.length < 6) { setError('密码至少 6 位'); return }
    if (password !== confirmPassword) { setError('两次密码不一致'); return }

    setLoading(true)
    try {
      const data = await setupPassword(password)
      setDisplayRecoveryCode(data.recovery_code)
      setStep('show_recovery')
    } catch (err) {
      setError(err.message || '设置失败')
    } finally {
      setLoading(false)
    }
  }

  // ===== 正常登录 =====
  const handleLogin = async (e) => {
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

  // ===== 重置密码 =====
  const handleReset = async (e) => {
    e.preventDefault()
    setError('')
    if (!recoveryCode.trim()) { setError('请输入恢复码'); return }
    if (!password) { setError('请输入新密码'); return }
    if (password.length < 6) { setError('新密码至少 6 位'); return }
    if (password !== confirmPassword) { setError('两次密码不一致'); return }

    setLoading(true)
    try {
      const data = await resetPassword(recoveryCode, password)
      setDisplayRecoveryCode(data.recovery_code)
      setPassword('')
      setConfirmPassword('')
      setRecoveryCode('')
      setStep('show_recovery')
    } catch (err) {
      setError(err.message || '重置失败')
    } finally {
      setLoading(false)
    }
  }

  // ===== 完成设置，跳转登录 =====
  const finishSetup = () => {
    setPassword('')
    setConfirmPassword('')
    setStep('login')
  }

  const sharedStyles = {
    formGroup: { marginBottom: 16, textAlign: 'left' },
    label: { display: 'block', marginBottom: 4, fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500 },
    input: {
      width: '100%', padding: '10px 12px', borderRadius: 8,
      border: '1px solid var(--border)', background: 'var(--bg)',
      color: 'var(--text)', fontSize: 14, outline: 'none', boxSizing: 'border-box',
    },
    btn: {
      width: '100%', padding: '12px', borderRadius: 8, border: 'none',
      background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
      color: '#fff', fontSize: 15, fontWeight: 600, cursor: 'pointer', marginTop: 8,
    },
    error: {
      background: 'var(--danger-light)', color: 'var(--danger)',
      padding: '8px 12px', borderRadius: 6, fontSize: 13, marginBottom: 12,
    },
    link: {
      display: 'block', textAlign: 'center', marginTop: 14, fontSize: 13,
      color: 'var(--primary)', cursor: 'pointer', textDecoration: 'none',
    },
  }

  // ===== Loading =====
  if (step === 'loading') {
    return (
      <div className="login-page">
        <div className="login-card" style={{ textAlign: 'center', padding: '40px 20px' }}>
          <div className="spinner" />
        </div>
      </div>
    )
  }

  // ===== 显示恢复码 =====
  if (step === 'show_recovery') {
    return (
      <div className="login-page">
        <div className="login-card" style={{ textAlign: 'center', maxWidth: 420 }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🔑</div>
          <h2 style={{ margin: 0 }}>请保存恢复码</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginTop: 8, lineHeight: 1.6 }}>
            此恢复码用于重置密码，<strong>仅显示一次</strong>，请妥善保存
          </p>
          <div style={{
            margin: '20px auto', padding: '16px 24px', fontSize: 24,
            fontFamily: 'monospace', fontWeight: 700, letterSpacing: 2,
            background: 'var(--bg-tertiary)', borderRadius: 12,
            color: 'var(--primary)', border: '2px dashed var(--border)',
            userSelect: 'all', wordBreak: 'break-all',
          }}>
            {displayRecoveryCode}
          </div>
          <div style={{
            background: 'var(--warning-light, #fff3cd)',
            color: 'var(--warning, #856404)', borderRadius: 8,
            padding: '10px 14px', fontSize: 12, textAlign: 'left', lineHeight: 1.6,
            marginBottom: 16,
          }}>
            ⚠️ 如果丢失恢复码且忘记密码，只能手动重置数据库。请截图或记录到安全的地方。
          </div>
          <button
            style={sharedStyles.btn}
            onClick={finishSetup}
          >我已保存，进入登录</button>
        </div>
      </div>
    )
  }

  // ===== 重置密码 =====
  if (step === 'reset') {
    return (
      <div className="login-page">
        <div className="login-card" style={{ maxWidth: 420 }}>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <div className="login-logo">
              <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="48" height="48" rx="12" fill="url(#loginGrad)" />
                <path d="M14 18a4 4 0 014-4h12a4 4 0 014 4v2a4 4 0 01-4 4h-8l-4 4v-4a4 4 0 01-4-4v-2z" fill="white" />
                <circle cx="21" cy="22" r="1.5" fill="#6366f1" />
                <circle cx="27" cy="22" r="1.5" fill="#6366f1" />
                <defs>
                  <linearGradient id="loginGrad" x1="0" y1="0" x2="48" y2="48">
                    <stop offset="0%" stopColor="#6366f1" />
                    <stop offset="100%" stopColor="#8b5cf6" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <h2 style={{ margin: '12px 0 0' }}>重置密码</h2>
          </div>

          <form onSubmit={handleReset}>
            <div style={sharedStyles.formGroup}>
              <label style={sharedStyles.label}>恢复码</label>
              <input
                style={sharedStyles.input}
                type="text"
                value={recoveryCode}
                onChange={e => { setRecoveryCode(e.target.value.toUpperCase()); setError('') }}
                placeholder="输入恢复码，格式如 ABCD-EFGH-IJKL"
                autoFocus
              />
            </div>
            <div style={sharedStyles.formGroup}>
              <label style={sharedStyles.label}>新密码（至少 6 位）</label>
              <input
                style={sharedStyles.input}
                type="password"
                value={password}
                onChange={e => { setPassword(e.target.value); setError('') }}
                placeholder="输入新密码"
              />
            </div>
            <div style={sharedStyles.formGroup}>
              <label style={sharedStyles.label}>确认新密码</label>
              <input
                style={sharedStyles.input}
                type="password"
                value={confirmPassword}
                onChange={e => { setConfirmPassword(e.target.value); setError('') }}
                placeholder="再次输入新密码"
              />
            </div>

            {error && <div style={sharedStyles.error}>{error}</div>}

            <button type="submit" className={`login-btn ${loading ? 'loading' : ''}`} disabled={loading} style={sharedStyles.btn}>
              {loading ? <span className="spinner" /> : '重置密码'}
            </button>

            <a style={sharedStyles.link} onClick={() => { setError(''); setStep('login') }}>← 返回登录</a>
          </form>
        </div>
      </div>
    )
  }

  // ===== 首次设置 =====
  if (step === 'setup') {
    return (
      <div className="login-page">
        <div className="login-card" style={{ maxWidth: 420 }}>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <div className="login-logo">
              <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="48" height="48" rx="12" fill="url(#loginGrad)" />
                <path d="M14 18a4 4 0 014-4h12a4 4 0 014 4v2a4 4 0 01-4 4h-8l-4 4v-4a4 4 0 01-4-4v-2z" fill="white" />
                <circle cx="21" cy="22" r="1.5" fill="#6366f1" />
                <circle cx="27" cy="22" r="1.5" fill="#6366f1" />
                <defs>
                  <linearGradient id="loginGrad" x1="0" y1="0" x2="48" y2="48">
                    <stop offset="0%" stopColor="#6366f1" />
                    <stop offset="100%" stopColor="#8b5cf6" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <h1>TG Chat Bot</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: 13, margin: 0 }}>首次使用，请设置管理密码</p>
          </div>

          <form onSubmit={handleSetup}>
            <div style={sharedStyles.formGroup}>
              <label style={sharedStyles.label}>管理密码（至少 6 位）</label>
              <input
                style={sharedStyles.input}
                type="password"
                value={password}
                onChange={e => { setPassword(e.target.value); setError('') }}
                placeholder="设置管理密码"
                autoFocus
              />
            </div>
            <div style={sharedStyles.formGroup}>
              <label style={sharedStyles.label}>确认密码</label>
              <input
                style={sharedStyles.input}
                type="password"
                value={confirmPassword}
                onChange={e => { setConfirmPassword(e.target.value); setError('') }}
                placeholder="再次输入密码"
              />
            </div>

            {error && <div style={sharedStyles.error}>{error}</div>}

            <button type="submit" className={`login-btn ${loading ? 'loading' : ''}`} disabled={loading} style={sharedStyles.btn}>
              {loading ? <span className="spinner" /> : '设置密码'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  // ===== 正常登录 =====
  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="48" height="48" rx="12" fill="url(#loginGrad)" />
            <path d="M14 18a4 4 0 014-4h12a4 4 0 014 4v2a4 4 0 01-4 4h-8l-4 4v-4a4 4 0 01-4-4v-2z" fill="white" />
            <circle cx="21" cy="22" r="1.5" fill="#6366f1" />
            <circle cx="27" cy="22" r="1.5" fill="#6366f1" />
            <defs>
              <linearGradient id="loginGrad" x1="0" y1="0" x2="48" y2="48">
                <stop offset="0%" stopColor="#6366f1" />
                <stop offset="100%" stopColor="#8b5cf6" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        <h1>TG Chat Bot</h1>
        <p className="login-subtitle">Telegram Bot 管理面板</p>

        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label>管理密码</label>
            <div className="login-input-wrap">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" width="18" height="18" className="login-input-icon">
                <rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0110 0v4" />
                <circle cx="12" cy="16" r="1" />
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
            {loading ? <span className="spinner" /> : '登录'}
          </button>
        </form>

        <a style={sharedStyles.link} onClick={() => { setError(''); setPassword(''); setConfirmPassword(''); setRecoveryCode(''); setStep('reset') }}>
          重置密码
        </a>
      </div>
    </div>
  )
}

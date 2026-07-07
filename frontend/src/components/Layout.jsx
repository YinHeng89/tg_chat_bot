import { useState, useRef, useEffect, createContext, useContext } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { apiPost } from '../api'
import { useTheme } from '../App'
import {
  IconDashboard, IconBot, IconCpu, IconPlug,
  IconShield, IconMessage, IconClock,
  IconActivity, IconLogout,
} from '../icons'

export const PageTitleContext = createContext(null)
export function usePageTitle(sub) {
  const setSub = useContext(PageTitleContext)
  useEffect(() => { if (setSub) setSub(sub) }, [sub, setSub])
}

const navItems = [
  { to: '/', icon: IconDashboard, label: '仪表盘', sub: '机器人运行状态概览' },
  { to: '/bots', icon: IconBot, label: 'Bot 管理', sub: '管理所有 Bot 实例、性格和运行参数' },
  { to: '/models', icon: IconCpu, label: '模型配置', sub: '第一个为主模型，后续为备用模型，主模型失败时自动切换' },
  { to: '/connectors', icon: IconPlug, label: '连接器管理', sub: '管理已安装的插件和扩展' },
  { to: '/blacklist', icon: IconShield, label: '黑名单', sub: '管理被禁止使用机器人的用户' },
  { to: '/sessions', icon: IconMessage, label: '会话管理', sub: '查看和清理活跃的对话会话' },
  { to: '/diagnostics', icon: IconActivity, label: '连接诊断', sub: 'Telegram 连接状态检测' },
  { to: '/tasks', icon: IconClock, label: '定时任务', sub: '管理待办提醒和定时通知' },
]

export default function Layout({ children, onLogout }) {
  const location = useLocation()
  const { cycleTheme, themeLabel } = useTheme()
  const currentNav = navItems.find(item =>
    item.to === '/' ? location.pathname === '/' : location.pathname.startsWith(item.to)
  )
  const [menuOpen, setMenuOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [pwdModal, setPwdModal] = useState(false)
  const [oldPwd, setOldPwd] = useState('')
  const [newPwd, setNewPwd] = useState('')
  const [pwdError, setPwdError] = useState('')
  const [changing, setChanging] = useState(false)
  const [pageSub, setPageSub] = useState('')
  const menuRef = useRef(null)

  // 切换路由时清空动态副标题并关闭侧边栏
  useEffect(() => { setPageSub(''); setSidebarOpen(false) }, [location.pathname])

  useEffect(() => {
    const handler = (e) => { if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleChangePwd = async () => {
    setPwdError('')
    if (!oldPwd || !newPwd) { setPwdError('请填写新旧密码'); return }
    setChanging(true)
    try {
      await apiPost('/auth/change-password', { old_password: oldPwd, new_password: newPwd })
      setPwdModal(false); setOldPwd(''); setNewPwd('')
      setMenuOpen(false)
    } catch (err) { setPwdError(err.message) }
    setChanging(false)
  }

  return (
    <div className="layout-v2">
      {/* 顶部导航栏 */}
      <header className="top-bar">
        <button className="hamburger-btn" onClick={() => setSidebarOpen(o => !o)} aria-label="菜单">
          <span className={`hamburger-line${sidebarOpen ? ' open' : ''}`}>
            <i></i><i></i><i></i>
          </span>
        </button>
        <div className="top-bar-left">
          <span className="logo-icon"><IconBot /></span>
          <span className="logo-text">TG Chat Bot</span>
        </div>
        <div className="top-bar-title">
          {currentNav && (
            <>
              <span className="top-bar-title-main">{currentNav.label}</span>
              <span className="top-bar-title-sub">{pageSub || currentNav.sub}</span>
            </>
          )}
        </div>
        <div className="top-bar-right" ref={menuRef}>
          <button className="theme-toggle-btn" onClick={cycleTheme} title={`主题：${themeLabel}`} aria-label="切换主题">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="5"/>
              <line x1="12" y1="1" x2="12" y2="3"/>
              <line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/>
              <line x1="21" y1="12" x2="23" y2="12"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
          </button>
          <button className="header-user-btn" onClick={() => setMenuOpen(o => !o)}>
            <span className="header-avatar">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: 14, height: 14 }}>
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v4"/><circle cx="12" cy="7" r="4"/>
              </svg>
            </span>
            <span className="header-user-label">管理员</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: 12, height: 12 }}>
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>
          {menuOpen && (
            <div className="header-dropdown">
              <button onClick={() => { setMenuOpen(false); setPwdModal(true); setOldPwd(''); setNewPwd(''); setPwdError('') }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                修改密码
              </button>
              <button onClick={() => { setMenuOpen(false); onLogout() }}>
                <IconLogout /> 退出登录
              </button>
            </div>
          )}
        </div>
      </header>

      {/* 侧边栏 + 内容 */}
      <div className="body-area">
        {/* 移动端侧边栏遮罩 */}
        <div className={`sidebar-overlay${sidebarOpen ? ' visible' : ''}`} onClick={() => setSidebarOpen(false)} />
        <aside className={`sidebar-v2${sidebarOpen ? ' sidebar-open' : ''}`}>
          <nav className="sidebar-nav">
            {navItems.map(item => (
              <NavLink key={item.to} to={item.to} end={item.to === '/'}
                className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                onClick={() => setSidebarOpen(false)}>
                <item.icon /><span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="main-content">
          <PageTitleContext.Provider value={setPageSub}>
            {children}
          </PageTitleContext.Provider>
        </main>
      </div>

      {/* 修改密码弹窗 */}
      {pwdModal && (
        <div className="modal-overlay-small" onClick={() => setPwdModal(false)}>
          <div className="modal-content-small" onClick={e => e.stopPropagation()}>
            <h3>修改密码</h3>
            <div className="form-group" style={{ marginTop: 12 }}>
              <label className="form-label">旧密码</label>
              <input className="form-input" type="password" value={oldPwd}
                onChange={e => setOldPwd(e.target.value)} placeholder="输入当前密码" />
            </div>
            <div className="form-group">
              <label className="form-label">新密码</label>
              <input className="form-input" type="password" value={newPwd}
                onChange={e => setNewPwd(e.target.value)} placeholder="至少 6 位" />
            </div>
            {pwdError && <div style={{ color: 'var(--danger)', fontSize: 12, marginBottom: 8 }}>{pwdError}</div>}
            <div className="modal-actions">
              <button className="btn btn-outline btn-sm" onClick={() => setPwdModal(false)}>取消</button>
              <button className="btn btn-primary btn-sm" onClick={handleChangePwd} disabled={changing}>
                {changing ? '修改中...' : '确认'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

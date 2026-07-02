import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import { IconPlug } from '../icons'
import { usePageTitle } from '../components/Layout'

export default function Connectors() {
  const [plugins, setPlugins] = useState([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)

  useEffect(() => { loadData() }, [])

  const loadData = () => {
    setLoading(true)
    apiGet('/plugins').then(d => setPlugins(d.plugins || [])).catch(console.error).finally(() => setLoading(false))
  }

  const toggle = async (p) => {
    try {
      await apiPost('/plugins/toggle', { name: p.name, enabled: !p.enabled })
      setPlugins(prev => prev.map(x => x.name === p.name ? { ...x, enabled: !x.enabled } : x))
      setToast({ type: 'success', text: `${p.name} ${!p.enabled ? '已启用' : '已禁用'}` })
    } catch (err) { setToast({ type: 'error', text: err.message }) }
    setTimeout(() => setToast(null), 3000)
  }

  const enabled = plugins.filter(p => p.enabled).length
  usePageTitle(`管理已安装的插件和扩展 · ${enabled}/${plugins.length} 已启用`)

  if (loading) return <div className="page-header"><h1>加载中...</h1></div>

  return (
    <div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.text}</div>}
      <div className="card">
        {plugins.map(p => (
          <div key={p.name} className="plugin-row">
            <div className="plugin-info">
              <h4>{p.name}</h4>
              <p>{p.description || ''}</p>
              <div className="plugin-cmd">
                {p.auto_trigger ? '自动触发' : ''}{p.manual_command ? ` | 命令: /${p.manual_command}` : ''}
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span className={`badge ${p.enabled ? 'badge-success' : 'badge-default'}`}>
                {p.enabled ? '开启' : '关闭'}
              </span>
              <label className="toggle">
                <input type="checkbox" checked={p.enabled} onChange={() => toggle(p)} />
                <span className="toggle-slider"></span>
              </label>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

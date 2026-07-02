import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import { IconSettings, IconSave } from '../icons'

export default function Settings({ selectedBotId }) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [bots, setBots] = useState([])
  const [botId, setBotId] = useState(selectedBotId)
  const [toast, setToast] = useState(null)
  const [form, setForm] = useState({
    group_auto_reply: 'true',
    group_reply_mode: 'mentioned',
    max_history: '20',
    rate_limit: '10',
    whitelist_mode: 'false',
  })

  useEffect(() => { setBotId(selectedBotId) }, [selectedBotId])

  useEffect(() => {
    apiGet('/bots').then(d => setBots(d.bots || [])).catch(() => {})
  }, [])

  useEffect(() => {
    if (!botId) { setLoading(false); return }
    setLoading(true)
    const prefix = `${botId}:`
    apiGet('/settings').then(data => {
      setForm({
        group_auto_reply: data[`${prefix}group_auto_reply`] || data.group_auto_reply || 'true',
        group_reply_mode: data[`${prefix}group_reply_mode`] || data.group_reply_mode || 'mentioned',
        max_history: data[`${prefix}max_history`] || data.max_history || '20',
        rate_limit: data[`${prefix}rate_limit`] || data.rate_limit || '10',
        whitelist_mode: data[`${prefix}whitelist_mode`] || data.whitelist_mode || 'false',
      })
    }).catch(console.error).finally(() => setLoading(false))
  }, [botId])

  const update = (key, value) => setForm(prev => ({ ...prev, [key]: value }))

  const handleSave = async () => {
    if (!botId) { setToast({ type: 'error', text: '请先选择 Bot' }); return }
    setSaving(true)
    const prefix = `${botId}:`
    try {
      await apiPost('/settings/batch', {
        settings: Object.fromEntries(
          Object.entries(form).map(([k, v]) => [`${prefix}${k}`, v])
        )
      })
      setToast({ type: 'success', text: '已保存' })
    } catch (err) {
      setToast({ type: 'error', text: err.message })
    } finally {
      setSaving(false)
      setTimeout(() => setToast(null), 3000)
    }
  }

  if (loading && botId) return <div className="page-header"><h1>Load...</h1></div>

  const boolVal = (key) => form[key] === 'true'

  return (
    <div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.text}</div>}
      <div className="page-header">
        <h1>系统设置</h1>
        <p>为指定 Bot 配置运行参数</p>
      </div>

      <div className="card">
        <div className="card-header"><IconSettings /> 基本设置</div>

        <div className="form-group">
          <label className="form-label">选择 Bot</label>
          <select className="form-select" value={botId} onChange={e => setBotId(e.target.value)}>
            <option value="">-- 选择 Bot --</option>
            {bots.map(b => (
              <option key={b.id} value={b.id}>{b.name || `Bot #${b.id}`}</option>
            ))}
          </select>
        </div>
      </div>

      {botId && (
        <>
          <div className="card">
            <div className="card-header"><IconSettings /> 群聊设置</div>
            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <label className="toggle">
                  <input type="checkbox" checked={boolVal('group_auto_reply')}
                    onChange={e => update('group_auto_reply', e.target.checked ? 'true' : 'false')} />
                  <span className="toggle-slider"></span>
                </label>
                群聊自动回复
              </label>
            </div>
            {boolVal('group_auto_reply') && (
              <div className="form-group">
                <label className="form-label">回复模式</label>
                <select className="form-select" value={form.group_reply_mode}
                  onChange={e => update('group_reply_mode', e.target.value)}>
                  <option value="mentioned">仅 @提及 时回复</option>
                  <option value="all">回复所有消息</option>
                </select>
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-header"><IconSettings /> 对话设置</div>
            <div className="form-group">
              <label className="form-label">上下文记忆轮数</label>
              <input className="form-input" type="number" min={1} max={100}
                value={form.max_history} onChange={e => update('max_history', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">频率限制（次/分钟）</label>
              <input className="form-input" type="number" min={0} max={60}
                value={form.rate_limit} onChange={e => update('rate_limit', e.target.value)} />
            </div>
          </div>

          <div className="card">
            <div className="card-header"><IconSettings /> 安全设置</div>
            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <label className="toggle">
                  <input type="checkbox" checked={boolVal('whitelist_mode')}
                    onChange={e => update('whitelist_mode', e.target.checked ? 'true' : 'false')} />
                  <span className="toggle-slider"></span>
                </label>
                白名单模式
              </label>
            </div>
          </div>

          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            <IconSave /> {saving ? '保存中...' : '保存设置'}
          </button>
        </>
      )}
    </div>
  )
}

import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import { IconSparkles, IconSave } from '../icons'

const IDENTITY = '你是运行在 Telegram 上的聊天机器人。你能接收群聊消息、获取群人数、回复消息。如果权限不足请说「没有此权限」而非「我不是机器人」。'

const PERSONALITY_PRESETS = {
  friendly: { label: '友好助手', prompt: `${IDENTITY} 请用友好、亲切的语气回复，像一个热心的群友。用简洁清晰的中文回答。`, desc: '友善、乐于助人' },
  professional: { label: '专业顾问', prompt: `${IDENTITY} 回答要严谨、准确、有深度，像一个专业的技术顾问。`, desc: '严谨专业' },
  humorous: { label: '幽默伙伴', prompt: `${IDENTITY} 用轻松诙谐的方式交流，适当加入幽默感。`, desc: '轻松幽默' },
  teacher: { label: '耐心导师', prompt: `${IDENTITY} 请像老师一样耐心讲解，循序渐进。`, desc: '循循善诱' },
  custom: { label: '自定义', prompt: IDENTITY, desc: '自由编写' }
}

export default function Personality({ selectedBotId }) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [bots, setBots] = useState([])
  const [botId, setBotId] = useState(selectedBotId)
  const [personality, setPersonality] = useState('friendly')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [toast, setToast] = useState(null)

  // 同步外部 selectedBotId
  useEffect(() => { setBotId(selectedBotId) }, [selectedBotId])

  // 加载 Bot 列表
  useEffect(() => {
    apiGet('/bots').then(d => setBots(d.bots || [])).catch(() => {})
  }, [])

  // Bot 变化时加载设置
  useEffect(() => {
    if (!botId) { setLoading(false); return }
    setLoading(true)
    const prefix = `${botId}:`
    apiGet('/settings').then(data => {
      setPersonality(data[`${prefix}bot_personality`] || data.bot_personality || 'friendly')
      setSystemPrompt(data[`${prefix}bot_system_prompt`] || data.bot_system_prompt || '')
    }).catch(console.error).finally(() => setLoading(false))
  }, [botId])

  const handlePreset = (key) => {
    setPersonality(key)
    const preset = PERSONALITY_PRESETS[key]
    if (preset && preset.prompt) setSystemPrompt(preset.prompt)
  }

  const handleSave = async () => {
    if (!botId) { setToast({ type: 'error', text: '请先选择 Bot' }); return }
    setSaving(true)
    const prefix = `${botId}:`
    try {
      await apiPost('/settings/batch', {
        settings: {
          [`${prefix}bot_personality`]: personality,
          [`${prefix}bot_system_prompt`]: systemPrompt,
        }
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

  return (
    <div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.text}</div>}
      <div className="page-header">
        <h1>机器人性格</h1>
        <p>设置 System Prompt 和对话风格</p>
      </div>

      <div className="card">
        <div className="card-header"><IconSparkles /> 基本设置</div>

        <div className="form-group">
          <label className="form-label">选择 Bot</label>
          <select className="form-select" value={botId} onChange={e => setBotId(e.target.value)}>
            <option value="">-- 选择 Bot --</option>
            {bots.map(b => (
              <option key={b.id} value={b.id}>{b.name || `Bot #${b.id}`}</option>
            ))}
          </select>
          {botId && (
            <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text-secondary)' }}>
              当前 Bot: <strong>{bots.find(b => String(b.id) === botId)?.name || `#${botId}`}</strong>
              （名称在 Bot 管理页修改）
            </div>
          )}
        </div>
      </div>

      {botId && (
        <>
          <div className="card">
            <div className="card-header"><IconSparkles /> 性格预设</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
              {Object.entries(PERSONALITY_PRESETS).map(([key, preset]) => (
                <div key={key} className={`model-card ${personality === key ? 'active' : ''}`}
                  style={{ cursor: 'pointer', padding: 14 }}
                  onClick={() => handlePreset(key)}>
                  <div className="model-card-header">
                    <h3 style={{ fontSize: 14 }}>{preset.label}</h3>
                    {personality === key && <span className="badge badge-success">当前</span>}
                  </div>
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{preset.desc}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-header"><IconSparkles /> System Prompt</div>
            <textarea className="form-textarea" rows={8} value={systemPrompt}
              onChange={e => setSystemPrompt(e.target.value)} placeholder="输入 System Prompt..." />
          </div>

          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            <IconSave /> {saving ? '保存中...' : '保存系统设置'}
          </button>
        </>
      )}
    </div>
  )
}

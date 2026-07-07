import { useState, useEffect, useRef } from 'react'
import { apiGet, apiPost, apiDelete } from '../api'
import { IconPlus, IconTrash, IconRefresh, IconActivity } from '../icons'
import Modal from '../components/Modal'

const IconClock = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12 6 12 12 16 14"/>
  </svg>
)

const IconHeart = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
  </svg>
)

const IconAi = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14 }}>
    <rect x="3" y="11" width="18" height="10" rx="2"/>
    <circle cx="12" cy="5" r="2"/>
    <path d="M12 7v4"/>
    <line x1="8" y1="16" x2="8" y2="16.01"/>
    <line x1="16" y1="16" x2="16" y2="16.01"/>
  </svg>
)

const IconManual = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 14, height: 14 }}>
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v4"/>
    <circle cx="12" cy="7" r="4"/>
  </svg>
)

const statusMap = {
  pending: { label: '待触发', className: 'badge-warning' },
  done:    { label: '已完成', className: 'badge-success' },
  skipped: { label: '已跳过', className: 'badge-muted' },
}

const repeatLabels = { daily: '每天', weekly: '每周', hourly: '每小时' }

export default function Tasks() {
  const [tasks, setTasks] = useState([])
  const [bots, setBots] = useState([])
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [tick, setTick] = useState(0)
  const reloadRef = useRef(false)
  const reloadedSet = useRef(new Set())

  // 心跳设置
  const [heartbeatModal, setHeartbeatModal] = useState(false)
  const [heartbeat, setHeartbeat] = useState({ enabled: false, bark_key: '', interval: '30' })

  // 删除确认
  const [deleteModal, setDeleteModal] = useState(null) // { id, title }

  const [form, setForm] = useState({
    title: '', fire_at: '', chat_id: '', bot_id: '', repeat_rule: ''
  })

  useEffect(() => { loadData(); loadHeartbeat() }, [])

  // 每秒刷新倒计时，无 pending 任务则停掉 interval
  useEffect(() => {
    const hasPending = tasks.some(t => t.status === 'pending')
    if (!hasPending) return
    const timer = setInterval(() => setTick(t => t + 1), 1000)
    return () => clearInterval(timer)
  }, [tasks])

  const loadData = () => {
    setLoading(true)
    Promise.all([
      apiGet('/tasks'),
      apiGet('/bots'),
      apiGet('/sessions'),
    ]).then(([taskData, botData, sessionData]) => {
      const newTasks = taskData.tasks || []
      setTasks(newTasks)
      setBots(botData.bots || [])
      setSessions(sessionData.sessions || [])
    }).catch(console.error).finally(() => {
      reloadRef.current = false
      setLoading(false)
    })
  }

  const openAdd = () => {
    const now = new Date()
    const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
    const defaultBot = bots.length > 0 ? String(bots[0].id) : ''
    const defaultChat = sessions.length > 0 ? String(sessions[0].chat_id) : ''
    setForm({ title: '', fire_at: local, chat_id: defaultChat, bot_id: defaultBot, repeat_rule: '' })
    setModalOpen(true)
  }

  const handleAdd = async () => {
    if (!form.title || !form.fire_at) return
    try {
      await apiPost('/tasks', {
        title: form.title,
        fire_at: form.fire_at.replace('T', ' ') + ':00',
        chat_id: form.chat_id,
        bot_id: parseInt(form.bot_id) || 0,
        user_id: 0,
        repeat_rule: form.repeat_rule,
      })
      setToast({ type: 'success', text: '任务已创建' })
      setModalOpen(false)
      reloadedSet.current.clear()
      loadData()
    } catch (err) { setToast({ type: 'error', text: err.message }) }
    setTimeout(() => setToast(null), 3000)
  }

  const handleDelete = async (id) => {
    setDeleteModal(null)
    try {
      await apiDelete(`/tasks/${id}`)
      setToast({ type: 'success', text: '任务已删除' })
      reloadedSet.current.clear()
      loadData()
    } catch (err) { setToast({ type: 'error', text: err.message }) }
    setTimeout(() => setToast(null), 3000)
  }

  const loadHeartbeat = () => {
    apiGet('/settings').then(d => {
      const settings = d || {}
      setHeartbeat({
        enabled: settings.heartbeat_enabled === 'true',
        bark_key: settings.heartbeat_bark_key || '',
        interval: settings.heartbeat_interval || '30',
      })
    }).catch(() => {})
  }

  const saveHeartbeat = async () => {
    try {
      await apiPost('/settings/batch', { settings: {
        heartbeat_enabled: String(heartbeat.enabled),
        heartbeat_bark_key: heartbeat.bark_key,
        heartbeat_interval: heartbeat.interval,
      }})
      setToast({ type: 'success', text: '心跳设置已保存' })
      setHeartbeatModal(false)
    } catch (err) { setToast({ type: 'error', text: err.message }) }
    setTimeout(() => setToast(null), 3000)
  }

  // tick 变化时检查是否有任务到期，触发一次 reload
  useEffect(() => {
    if (reloadRef.current) return
    const hasExpired = tasks.some(t => {
      if (t.status !== 'pending' || reloadedSet.current.has(t.id)) return false
      const diff = new Date((t.fire_at || '').replace(' ', 'T')) - new Date()
      return diff <= 0
    })
    if (hasExpired) {
      reloadRef.current = true
      tasks.forEach(t => {
        if (t.status === 'pending') {
          const diff = new Date((t.fire_at || '').replace(' ', 'T')) - new Date()
          if (diff <= 0) reloadedSet.current.add(t.id)
        }
      })
      loadData()
    }
  }, [tick])

  const countdown = (fireAt) => {
    if (!fireAt) return { text: '-', expired: true }
    const diff = new Date(fireAt.replace(' ', 'T')) - new Date()
    if (diff <= 0) return { text: '已到期', expired: true }
    const h = Math.floor(diff / 3600000)
    const m = Math.floor((diff % 3600000) / 60000)
    const s = Math.floor((diff % 60000) / 1000)
    if (h > 0) return { text: `${h}h${m}m${s}s`, expired: false }
    return { text: `${m}m${s}s`, expired: false }
  }

  const getSessionLabel = (chatId) => {
    const s = sessions.find(s => String(s.chat_id) === String(chatId))
    if (s && s.chat_title) return `${s.chat_title} (${chatId})`
    return chatId || '-'
  }

  const getBotLabel = (botId) => {
    const b = bots.find(b => b.id === botId)
    return b ? `#${b.id} ${b.name}` : (botId ? `#${botId}` : '-')
  }

  if (loading) return <div className="page-header"><h1>加载中...</h1></div>

  const pending = tasks.filter(t => t.status === 'pending').length

  return (
    <div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.text}</div>}

      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        <button className="btn btn-primary" onClick={openAdd}>
          <IconPlus /> 新建任务
        </button>
        <button className="btn btn-outline" onClick={loadData}>
          <IconRefresh /> 刷新
        </button>
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          {pending} 个待触发
        </span>
        <div style={{ flex: 1 }} />
        <button
          className={`btn ${heartbeat.enabled && heartbeat.bark_key ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setHeartbeatModal(true)}>
          <IconHeart /> 心跳 {heartbeat.enabled && heartbeat.bark_key ? '✓' : ''}
        </button>
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="新建定时任务">
        <div className="form-group">
          <label className="form-label">提醒内容 *</label>
          <input className="form-input" value={form.title}
            onChange={e => setForm({ ...form, title: e.target.value })}
            placeholder="例：开会、吃药、检查服务器" />
        </div>
        <div className="form-group">
          <label className="form-label">触发时间 *</label>
          <input className="form-input" type="datetime-local" value={form.fire_at}
            onChange={e => setForm({ ...form, fire_at: e.target.value })} />
        </div>
        <div className="form-group">
          <label className="form-label">目标会话 *</label>
          <select className="form-input" value={form.chat_id}
            onChange={e => setForm({ ...form, chat_id: e.target.value })}>
            <option value="">-- 请选择 --</option>
            {sessions.map(s => (
              <option key={s.chat_id} value={s.chat_id}>
                {s.chat_title || s.chat_id} ({s.chat_id})
              </option>
            ))}
          </select>
          {sessions.length === 0 && (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
              暂无可用会话，请先让 Bot 加入群聊或私聊
            </div>
          )}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div className="form-group">
            <label className="form-label">机器人</label>
            <select className="form-input" value={form.bot_id}
              onChange={e => setForm({ ...form, bot_id: e.target.value })}>
              <option value="">-- 自动选择 --</option>
              {bots.filter(b => b.is_active).map(b => (
                <option key={b.id} value={b.id}>#{b.id} {b.name}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">重复规则</label>
            <select className="form-input" value={form.repeat_rule}
              onChange={e => setForm({ ...form, repeat_rule: e.target.value })}>
              <option value="">单次</option>
              <option value="daily">每天</option>
              <option value="weekly">每周</option>
              <option value="hourly">每小时</option>
            </select>
          </div>
        </div>
        <div className="modal-actions">
          <button className="btn btn-outline btn-sm" onClick={() => setModalOpen(false)}>取消</button>
          <button className="btn btn-primary btn-sm" onClick={handleAdd}><IconPlus /> 创建</button>
        </div>
      </Modal>

      <Modal open={heartbeatModal} onClose={() => setHeartbeatModal(false)} title="Bark 心跳推送设置">
        <div style={{ marginBottom: 12, fontSize: 13, color: 'var(--text-muted)' }}>
          开启后，Bot 会定期通过 Bark 推送运行状态到你的手机。
        </div>
        <div className="form-group">
          <label className="form-label">
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input type="checkbox" checked={heartbeat.enabled}
                onChange={e => setHeartbeat({ ...heartbeat, enabled: e.target.checked })} />
              启用心跳推送
            </label>
          </label>
        </div>
        <div className="form-group">
          <label className="form-label">Bark 推送地址 *</label>
          <input className="form-input" value={heartbeat.bark_key}
            onChange={e => setHeartbeat({ ...heartbeat, bark_key: e.target.value })}
            placeholder="设备 Key 或完整 URL（如 uecwxxx 或 https://bark.example.com/uecwxxx）" />
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
            官方服务填设备 Key，自建服务填完整地址
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">推送间隔（分钟）</label>
          <input className="form-input" type="number" min="5" max="1440" value={heartbeat.interval}
            onChange={e => setHeartbeat({ ...heartbeat, interval: e.target.value })}
            placeholder="30" />
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
            默认 30 分钟，建议 5~60 分钟
          </div>
        </div>
        <div className="modal-actions">
          <button className="btn btn-outline btn-sm" onClick={() => setHeartbeatModal(false)}>取消</button>
          <button className="btn btn-primary btn-sm" onClick={saveHeartbeat}><IconActivity /> 保存</button>
        </div>
      </Modal>

      <div className="card">
        <div className="card-header"><IconClock /> 定时任务列表 ({tasks.length})</div>
        {tasks.length === 0 ? (
          <div className="empty-state"><IconClock /><p>暂无定时任务，对话中说「提醒我…」即可自动创建</p></div>
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>内容</th>
                  <th>目标会话</th>
                  <th>触发时间</th>
                  <th>倒计时</th>
                  <th>来源</th>
                  <th>重复</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map(t => {
                  const st = statusMap[t.status] || { label: t.status, className: '' }
                  const isAi = t.user_id && t.user_id !== 0
                  const cd = t.status === 'pending' ? countdown(t.fire_at) : { text: '-', expired: true }
                  return (
                    <tr key={t.id}>
                      <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {t.title}
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        <div>{getSessionLabel(t.chat_id)}</div>
                        <div style={{ fontSize: 11 }}>Bot: {getBotLabel(t.bot_id)}</div>
                      </td>
                      <td style={{ whiteSpace: 'nowrap', fontSize: 13 }}>{t.fire_at || '-'}</td>
                      <td style={{ whiteSpace: 'nowrap', fontSize: 13, minWidth: 90, fontVariantNumeric: 'tabular-nums', color: cd.expired ? 'var(--danger)' : 'var(--text-muted)' }}>
                        {cd.text}
                      </td>
                      <td style={{ fontSize: 12, whiteSpace: 'nowrap', minWidth: 60 }}>
                        {isAi ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}><IconAi />AI</span>
                               : <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}><IconManual />手动</span>}
                      </td>
                      <td style={{ fontSize: 13 }}>
                        {repeatLabels[t.repeat_rule] || (t.repeat_rule || '-')}
                      </td>
                      <td><span className={`badge ${st.className}`}>{st.label}</span></td>
                      <td>
                        <button className="btn btn-outline btn-sm"
                          onClick={() => setDeleteModal({ id: t.id, title: t.title })}>
                          <IconTrash />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Modal open={!!deleteModal} onClose={() => setDeleteModal(null)} title="确认删除">
        <p style={{ marginBottom: 16 }}>确定要删除任务「<b>{deleteModal?.title}</b>」吗？</p>
        <div className="modal-actions">
          <button className="btn btn-outline btn-sm" onClick={() => setDeleteModal(null)}>取消</button>
          <button className="btn btn-danger btn-sm" onClick={() => handleDelete(deleteModal?.id)}>
            <IconTrash /> 确认删除
          </button>
        </div>
      </Modal>
    </div>
  )
}

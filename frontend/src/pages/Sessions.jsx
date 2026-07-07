import { useState, useEffect } from 'react'
import { apiGet, apiPost, apiDelete } from '../api'
import { IconMessage, IconTrash, IconRefresh, IconShield, IconUser, IconUsers } from '../icons'
import Modal from '../components/Modal'

export default function Sessions() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)
  const [clearModal, setClearModal] = useState(false)
  const [clearChatId, setClearChatId] = useState(null)
  const [clearing, setClearing] = useState(false)

  useEffect(() => { loadSessions() }, [])

  const loadSessions = () => {
    setLoading(true)
    apiGet('/sessions').then(d => setSessions(d.sessions || [])).catch(console.error).finally(() => setLoading(false))
  }

  const handleDelete = (chatId) => { setClearChatId(chatId); setClearModal(true) }
  const confirmClear = async () => {
    setClearing(true)
    try {
      await apiDelete(`/sessions/${clearChatId}`)
      setSessions(prev => prev.filter(s => s.chat_id !== clearChatId))
      setClearModal(false)
      setToast({ type: 'success', text: '会话已清空' })
    } catch (err) { setToast({ type: 'error', text: err.message }) }
    setClearing(false)
    setTimeout(() => setToast(null), 3000)
  }

  const handleBan = async (userId, chatId) => {
    try {
      await apiPost('/blacklist/add', { user_id: userId, reason: `会话 ${chatId}` })
      setToast({ type: 'success', text: `用户 ${userId} 已加入黑名单` })
    } catch (err) { setToast({ type: 'error', text: err.message }) }
    setTimeout(() => setToast(null), 3000)
  }

  if (loading) return <div className="page-header"><h1>加载中...</h1></div>

  return (
    <div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.text}</div>}
      <div className="card">
        <div className="card-header">
          <IconMessage /> 活跃会话 ({sessions.length})
          <button className="btn btn-outline btn-sm" onClick={loadSessions} style={{ marginLeft: 'auto' }}>
            <IconRefresh /> 刷新
          </button>
        </div>
        {sessions.length === 0 ? (
          <div className="empty-state"><IconMessage /><p>暂无活跃会话</p></div>
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead><tr><th>名称</th><th>会话 ID</th><th>用户 ID</th><th>消息数</th><th>Token</th><th>最近模型</th><th>最后活跃</th><th>操作</th></tr></thead>
              <tbody>
                {sessions.map(s => {
                  const isGroup = String(s.chat_id).startsWith('-')
                  const name = s.chat_title || (isGroup ? `群 ${s.chat_id}` : `用户 ${s.user_id}`)
                  return (
                  <tr key={s.chat_id}>
                    <td>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4, maxWidth: 160 }}
                        title={name}>
                        <span style={{ flexShrink: 0, color: isGroup ? 'var(--warning)' : 'var(--text-muted)', display: 'flex', width: 14, height: 14 }}>
                          {isGroup ? <IconUsers /> : <IconUser />}
                        </span>
                        <span style={{ fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {name}
                        </span>
                      </span>
                    </td>
                    <td><code>{s.chat_id}</code></td>
                    <td>{s.user_id}</td>
                    <td>{s.message_count || 0}</td>
                    <td>{(s.total_tokens || 0).toLocaleString()}</td>
                    <td><span className="badge badge-default">{s.model || '-'}</span></td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>{s.updated_at || '-'}</td>
                    <td>
                      <div className="action-btns" style={{ display: 'flex', gap: 4 }}>
                        <button className="btn btn-outline btn-sm" onClick={() => handleBan(s.user_id, s.chat_id)}>
                          <IconShield /> 拉黑
                        </button>
                        <button className="btn btn-outline btn-sm" onClick={() => handleDelete(s.chat_id)}>
                          <IconTrash /> 清空
                        </button>
                      </div>
                    </td>
                  </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 清空确认弹窗 */}
      <Modal open={clearModal} onClose={() => !clearing && setClearModal(false)}
        title="清空会话" width="400px">
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <div style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.8, marginBottom: 8 }}>
            确定要清空会话
            <strong style={{ color: 'var(--danger)' }}>「{clearChatId}」</strong>
            吗？
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>将删除该会话的所有聊天记录和上下文记忆，不可恢复</div>
        </div>
        <div className="modal-actions">
          <button className="btn btn-outline btn-sm" onClick={() => setClearModal(false)} disabled={clearing}>取消</button>
          <button className="btn btn-danger btn-sm" onClick={confirmClear} disabled={clearing}><IconTrash /> {clearing ? '清空中...' : '确认清空'}</button>
        </div>
      </Modal>
    </div>
  )
}

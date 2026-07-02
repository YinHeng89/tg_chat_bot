import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import { IconShield, IconPlus, IconTrash } from '../icons'
import Modal from '../components/Modal'

export default function Blacklist() {
  const [blacklist, setBlacklist] = useState([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({ user_id: '', reason: '' })

  useEffect(() => { loadData() }, [])

  const loadData = () => {
    setLoading(true)
    apiGet('/blacklist').then(d => setBlacklist(d.blacklist || [])).catch(console.error).finally(() => setLoading(false))
  }

  const openAdd = () => { setForm({ user_id: '', reason: '' }); setModalOpen(true) }

  const handleAdd = async () => {
    if (!form.user_id) return
    try {
      await apiPost('/blacklist/add', { user_id: parseInt(form.user_id), reason: form.reason })
      setToast({ type: 'success', text: `用户 ${form.user_id} 已加入黑名单` })
      setModalOpen(false)
      loadData()
    } catch (err) { setToast({ type: 'error', text: err.message }) }
    setTimeout(() => setToast(null), 3000)
  }

  const handleRemove = async (id) => {
    try {
      await apiPost('/blacklist/remove', { user_id: id })
      setToast({ type: 'success', text: `用户 ${id} 已移出黑名单` })
      loadData()
    } catch (err) { setToast({ type: 'error', text: err.message }) }
    setTimeout(() => setToast(null), 3000)
  }

  if (loading) return <div className="page-header"><h1>加载中...</h1></div>

  return (
    <div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.text}</div>}
      <button className="btn btn-primary" onClick={openAdd} style={{ marginBottom: 16 }}>
        <IconPlus /> 添加黑名单
      </button>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="添加黑名单">
        <div className="form-group">
          <label className="form-label">Telegram 用户 ID</label>
          <input className="form-input" type="number" value={form.user_id} onChange={e => setForm({ ...form, user_id: e.target.value })} placeholder="输入用户 ID" />
        </div>
        <div className="form-group">
          <label className="form-label">原因（可选）</label>
          <input className="form-input" value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} placeholder="拉黑原因" />
        </div>
        <div className="modal-actions">
          <button className="btn btn-outline btn-sm" onClick={() => setModalOpen(false)}>取消</button>
          <button className="btn btn-danger btn-sm" onClick={handleAdd}><IconPlus /> 加入黑名单</button>
        </div>
      </Modal>

      <div className="card">
        <div className="card-header"><IconShield /> 黑名单列表 ({blacklist.length})</div>
        {blacklist.length === 0 ? (
          <div className="empty-state"><IconShield /><p>黑名单为空</p></div>
        ) : (
          <table className="table">
            <thead><tr><th>用户 ID</th><th>原因</th><th>添加时间</th><th>操作</th></tr></thead>
            <tbody>
              {blacklist.map(item => (
                <tr key={item.user_id}>
                  <td><code>{item.user_id}</code></td>
                  <td>{item.reason || '-'}</td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>{item.added_at || '-'}</td>
                  <td>
                    <button className="btn btn-outline btn-sm" onClick={() => handleRemove(item.user_id)}>
                      <IconTrash /> 移除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

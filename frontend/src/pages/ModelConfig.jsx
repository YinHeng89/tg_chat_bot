import { useState, useEffect, useCallback } from 'react'
import { apiGet, apiPost, apiDelete } from '../api'
import { IconCpu, IconSave, IconPlus, IconTrash, IconZap } from '../icons'
import Modal from '../components/Modal'

const PROVIDERS = {
  mainstream: [
    { value: 'openai', label: 'OpenAI', defaultUrl: 'https://api.openai.com/v1', defaultModel: 'gpt-4o-mini' },
    { value: 'deepseek', label: 'DeepSeek', defaultUrl: 'https://api.deepseek.com', defaultModel: 'deepseek-chat' },
    { value: 'anthropic', label: 'Anthropic Claude', defaultUrl: '', defaultModel: 'claude-sonnet-4-20250514' },
    { value: 'gemini', label: 'Google Gemini', defaultUrl: 'https://generativelanguage.googleapis.com/v1beta/openai', defaultModel: 'gemini-2.0-flash' },
    { value: 'qwen', label: '通义千问 (Qwen)', defaultUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', defaultModel: 'qwen-plus' },
    { value: 'moonshot', label: 'Moonshot (Kimi)', defaultUrl: 'https://api.moonshot.cn/v1', defaultModel: 'moonshot-v1-8k' },
    { value: 'zhipu', label: '智谱 GLM', defaultUrl: 'https://open.bigmodel.cn/api/paas/v4', defaultModel: 'glm-4-flash' },
    { value: 'stepfun', label: '阶跃星辰 (Step)', defaultUrl: 'https://api.stepfun.com/v1', defaultModel: 'step-1-8k' },
    { value: 'minimax', label: 'MiniMax', defaultUrl: 'https://api.minimax.chat/v1', defaultModel: 'abab6.5s-chat' },
    { value: 'baidu', label: '百度文心 (ERNIE)', defaultUrl: 'https://qianfan.baidubce.com/v2', defaultModel: 'ernie-speed-128k' },
    { value: 'bytedance', label: '字节豆包 (Doubao)', defaultUrl: 'https://ark.cn-beijing.volces.com/api/v3', defaultModel: 'doubao-pro-32k' },
  ],
  local: [
    { value: 'ollama', label: 'Ollama 本地', defaultUrl: 'http://localhost:11434', defaultModel: 'qwen2.5:7b' },
  ],
  custom: [
    { value: 'custom', label: '自定义 (OpenAI 兼容)', defaultUrl: '', defaultModel: '' },
  ],
}
const ALL_PROVIDERS = [...PROVIDERS.mainstream, ...PROVIDERS.local, ...PROVIDERS.custom]

export default function ModelConfig() {
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ name: '', provider: 'openai', api_key: '', base_url: '', model_name: '', is_enabled: false })
  const [queriedModels, setQueriedModels] = useState([])
  const [visionMap, setVisionMap] = useState({})
  const [queryLoading, setQueryLoading] = useState(false)
  const [queryError, setQueryError] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [hoveredRowId, setHoveredRowId] = useState(null)
  const [deleteModal, setDeleteModal] = useState(false)
  const [deleteModelId, setDeleteModelId] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  useEffect(() => { loadData() }, [])

  const loadData = () => {
    setLoading(true)
    apiGet('/models').then(d => setModels(d.models || [])).catch(console.error).finally(() => setLoading(false))
  }

  const queryModels = useCallback(async (provider, baseUrl, apiKey) => {
    if (!baseUrl || !apiKey) return
    setQueryLoading(true)
    setQueryError('')
    setQueriedModels([])
    try {
      const res = await apiPost('/models/query-list', { provider, base_url: baseUrl, api_key: apiKey })
      if (res.models) { setQueriedModels(res.models); setVisionMap(res.vision || {}) }
      if (res.error) setQueryError(res.error)
    } catch (e) {
      setQueryError(e.message)
    }
    setQueryLoading(false)
  }, [])

  const testModel = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await apiPost('/models/test', {
        provider: form.provider, base_url: form.base_url, api_key: form.api_key, model_name: form.model_name,
      })
      setTestResult(res)
    } catch (e) {
      setTestResult({ success: false, error: e.message })
    }
    setTesting(false)
  }

  const openAdd = () => {
    setEditing(null)
    setQueriedModels([]); setQueryError(''); setTestResult(null)
    setForm({ name: '', provider: 'openai', api_key: '', base_url: 'https://api.openai.com/v1', model_name: '', is_enabled: false })
    setModalOpen(true)
  }

  const openEdit = async (m) => {
    setEditing(m.id)
    setQueriedModels([]); setQueryError(''); setTestResult(null)
    setShowApiKey(false)
    // 拉取真实 API Key（列表接口返回的是脱敏的）
    let realKey = ''
    try {
      const detail = await apiGet(`/models/${m.id}`)
      realKey = detail.api_key || ''
    } catch (e) { /* 降级 */ }
    setForm({ name: m.name, provider: m.provider, api_key: realKey, base_url: m.base_url || '', model_name: m.model_name || '', is_enabled: m.is_enabled })
    setModalOpen(true)
  }

  const closeModal = () => { setModalOpen(false); setTestResult(null) }

  const handleProviderChange = (provider) => {
    const info = ALL_PROVIDERS.find(p => p.value === provider)
    setForm({ ...form, provider, base_url: info?.defaultUrl || '', model_name: '' })
    setQueriedModels([])
    setQueryError('')
  }

  const handleSave = async () => {
    if (saving) return; setSaving(true)
    try {
      const payload = { ...form }
      if (!payload.api_key) delete payload.api_key
      if (editing) {
        await apiPost(`/models/${editing}`, payload)
        setToast({ type: 'success', text: '已保存' })
      } else {
        await apiPost('/models', payload)
        setToast({ type: 'success', text: '模型已添加' })
      }
      closeModal()
      loadData()
    } catch (err) { setToast({ type: 'error', text: err.message }) }
    setSaving(false); setTimeout(() => setToast(null), 3000)
  }

  const handleDelete = (id) => { setDeleteModelId(id); setDeleteModal(true) }
  const confirmDelete = async () => {
    setDeleting(true)
    try { await apiDelete(`/models/${deleteModelId}`); setDeleteModal(false); setToast({ type: 'success', text: '已删除' }); loadData() }
    catch (err) { setToast({ type: 'error', text: err.message }) }
    setDeleting(false)
    setTimeout(() => setToast(null), 3000)
  }

  const handleToggle = async (m) => {
    try {
      await apiPost(`/models/${m.id}`, { is_enabled: !m.is_enabled })
      setModels(prev => prev.map(x => x.id === m.id ? { ...x, is_enabled: !x.is_enabled } : x))
    } catch (err) { setToast({ type: 'error', text: err.message }); setTimeout(() => setToast(null), 3000) }
  }

  const setPrimary = async (id) => {
    try {
      await apiPost(`/models/${id}/set-primary`, {})
      loadData()
      setToast({ type: 'success', text: '主模型已切换' })
    } catch (err) { setToast({ type: 'error', text: err.message }) }
    setTimeout(() => setToast(null), 3000)
  }

  // 视觉能力二态切换：点击在启用/禁用之间切换
  const toggleVision = async (m) => {
    try {
      const newVision = !(m.capabilities?.vision || false)
      const res = await apiPost(`/models/${m.id}/vision`, { vision: newVision })
      setModels(prev => prev.map(x => x.id === m.id ? { ...x, capabilities: res.capabilities } : x))
      setToast({ type: 'success', text: newVision ? '已启用视觉能力' : '已禁用视觉能力' })
      setTimeout(() => setToast(null), 2000)
    } catch (err) { setToast({ type: 'error', text: err.message }); setTimeout(() => setToast(null), 3000) }
  }

  if (loading) return <div className="page-header"><h1>加载中...</h1></div>

  const sortedModels = [...models].sort((a, b) => a.sort_order - b.sort_order)

  return (
    <div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.text}</div>}
      <button className="btn btn-primary" onClick={openAdd} style={{ marginBottom: 16 }}>
        <IconPlus /> 添加模型
      </button>

      <Modal open={modalOpen} onClose={closeModal} title={editing ? '编辑模型' : '添加模型'} width="600px">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {/* 名称 */}
          <div className="form-group">
            <label className="form-label">名称</label>
            <input className="form-input form-input-sm" value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              placeholder="显示名称，如: GPT-4o" />
          </div>

          {/* 服务商 */}
          <div className="form-group">
            <label className="form-label">服务商</label>
            <select className="form-select" value={form.provider} onChange={e => {
              const p = e.target.value
              handleProviderChange(p)
            }} style={{ padding: '6px 10px', fontSize: 13 }}>
              <optgroup label="主流供应商">
                {PROVIDERS.mainstream.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </optgroup>
              <optgroup label="本地部署">
                {PROVIDERS.local.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </optgroup>
              <optgroup label="自定义">
                {PROVIDERS.custom.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </optgroup>
            </select>
          </div>

          {/* 地址 */}
          <div className="form-group">
            <label className="form-label">API 地址</label>
            <input className="form-input form-input-sm" value={form.base_url}
              onChange={e => setForm({ ...form, base_url: e.target.value })}
              placeholder={form.provider === 'anthropic' ? 'Claude 不需要填地址' : 'API 地址'} />
          </div>

          {/* API Key */}
          <div className="form-group">
            <label className="form-label">API Key</label>
            <div style={{ position: 'relative' }}>
              <input className="form-input form-input-sm" type={showApiKey ? 'text' : 'password'}
                value={form.api_key}
                onChange={e => setForm({ ...form, api_key: e.target.value })}
                placeholder={editing && !form.api_key ? '留空不修改' : '输入 API Key'}
                style={{ paddingRight: 36 }} />
              <button type="button" onClick={() => setShowApiKey(s => !s)}
                style={{
                  position: 'absolute', right: 6, top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', cursor: 'pointer', padding: 2, lineHeight: 1,
                  color: 'var(--text-muted)',
                }} title={showApiKey ? '隐藏' : '显示'}>
                {showApiKey ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/><path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/>
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* 选择模型 */}
          <div className="form-group">
            <label className="form-label">选择模型</label>
            <div style={{ display: 'flex', gap: 6 }}>
              <input className="form-input form-input-sm" value={form.model_name}
                onChange={e => {
                  setForm({ ...form, model_name: e.target.value, name: form.name || e.target.value })
                }}
                placeholder="输入或点下方模型..."
                style={{ flex: 1 }} />
              <button className="btn btn-outline btn-sm" onClick={() => queryModels(form.provider, form.base_url, form.api_key)}
                disabled={queryLoading || !form.base_url || !form.api_key}
                style={{ whiteSpace: 'nowrap' }}>
                {queryLoading ? '查询中...' : '查询模型'}
              </button>
              <button className="btn btn-outline btn-sm" onClick={testModel}
                disabled={testing || !form.api_key || !form.model_name}
                style={{ whiteSpace: 'nowrap' }}>
                {testing ? '测试中...' : '测试'}
              </button>
            </div>
            {testResult && (
              <div style={{ fontSize: 12, padding: '6px 10px', borderRadius: 6, marginTop: 4,
                background: testResult.success ? 'var(--success-light)' : 'var(--danger-light)',
                color: testResult.success ? 'var(--success)' : 'var(--danger)', }}>
                {testResult.success
                  ? `✅ ${testResult.reply}  (prompt: ${testResult.prompt_tokens}, completion: ${testResult.completion_tokens})`
                  : `❌ ${testResult.error}`
                }
              </div>
            )}
            {queryError && <div className="form-hint" style={{ color: 'var(--danger)' }}>查询失败：{queryError}</div>}
            {queriedModels.length > 0 && !queryError && (
              <div style={{ maxHeight: 180, overflowY: 'auto', border: '1px solid var(--border)', borderRadius: 6, marginTop: 4, padding: 4 }}>
                {queriedModels.map(m => {
                  const selected = form.model_name === m
                  return (
                    <div key={m} onClick={() => {
                      setForm({ ...form, model_name: m, name: form.name || m })
                    }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 6,
                        padding: '5px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 12,
                        background: selected ? 'var(--primary-light)' : 'transparent',
                        color: selected ? 'var(--primary)' : 'var(--text)',
                      }}>
                      <span style={{ flex: 1 }}>{m}</span>
                      {visionMap[m] && <span style={{ fontSize: 10, color: 'var(--success)', background: 'var(--success-light)', padding: '1px 5px', borderRadius: 3 }}>视觉</span>}
                    </div>
                  )
                })}
              </div>
            )}
            {form.provider === 'anthropic' && (
              <div className="form-hint">Claude 需手动输入模型名称</div>
            )}
          </div>
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, marginTop: 8 }}>
          <label className="toggle toggle-sm">
            <input type="checkbox" checked={form.is_enabled} onChange={e => setForm({ ...form, is_enabled: e.target.checked })} />
            <span className="toggle-slider"></span>
          </label>
          启用此模型
        </label>
        <div className="modal-actions" style={{ marginTop: 12 }}>
          <button className="btn btn-outline btn-sm" onClick={closeModal}>取消</button>
          <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}><IconSave /> {saving ? '保存中...' : '保存'}</button>
        </div>
      </Modal>

      <div className="card">
        <div className="card-header"><IconCpu /> 模型列表（{sortedModels.length} 个）</div>
        {sortedModels.length === 0 ? (
          <div className="empty-state"><IconCpu /><p>暂无模型，请添加</p></div>
        ) : (
          <table className="table">
            <thead><tr><th>顺序</th><th>名称</th><th>供应商</th><th>模型</th><th>Key</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              {sortedModels.map((m) => (
                <tr key={m.id}
                  style={m.is_primary ? { background: 'var(--primary-light)' } : {}}
                  onMouseEnter={() => setHoveredRowId(m.id)}
                  onMouseLeave={() => setHoveredRowId(null)}>
                  <td>{m.is_primary ? <span className="badge badge-success">主</span> : <span className="badge badge-default">备用</span>}</td>
                  <td><strong>{m.name || '-'}</strong></td>
                  <td>{ALL_PROVIDERS.find(p => p.value === m.provider)?.label || m.provider}</td>
                  <td>
                    {m.model_name || '-'}
                    {(() => {
                      const vision = !!(m.capabilities?.vision)
                      return (
                        <span
                          onClick={() => toggleVision(m)}
                          style={{
                            marginLeft: 4, fontSize: 10, padding: '1px 6px', cursor: 'pointer',
                            background: vision ? 'var(--success-light)' : 'var(--bg-tertiary)',
                            color: vision ? 'var(--success)' : 'var(--text-muted)',
                            borderRadius: 10, border: '1px solid currentColor',
                            userSelect: 'none', display: 'inline-block', lineHeight: '14px',
                          }}
                          title={vision ? '点击禁用视觉能力' : '点击启用视觉能力'}
                        >视觉</span>
                      )
                    })()}
                    {m.capabilities?.available != null && (
                      m.capabilities.available
                        ? <span className="badge badge-success" style={{ marginLeft: 4, fontSize: 10, padding: '1px 5px' }}>可用</span>
                        : <span className="badge" style={{ marginLeft: 4, fontSize: 10, padding: '1px 5px', background: 'var(--danger-light)', color: 'var(--danger)' }}>不可用</span>
                    )}
                  </td>
                  <td style={{ fontSize: 12 }}>{m.has_api_key ? m.api_key : <span style={{ color: 'var(--danger)' }}>未配置</span>}</td>
                  <td>
                    <label className="toggle toggle-sm" style={{ verticalAlign: 'middle' }}>
                      <input type="checkbox" checked={m.is_enabled} onChange={() => handleToggle(m)} />
                      <span className="toggle-slider"></span>
                    </label>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn btn-outline btn-sm" onClick={() => openEdit(m)}><IconSave /> 编辑</button>
                      <button className="btn btn-outline btn-sm" onClick={() => handleDelete(m.id)}><IconTrash /> 删除</button>
                      {!m.is_primary && (
                        <button className="btn btn-outline btn-sm" onClick={() => setPrimary(m.id)}
                          style={{ opacity: hoveredRowId === m.id ? 1 : 0, transition: 'opacity .15s' }}>
                          <IconZap /> 设为主模型
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 删除确认弹窗 */}
      <Modal open={deleteModal} onClose={() => !deleting && setDeleteModal(false)}
        title="删除模型" width="400px">
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <div style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.8, marginBottom: 8 }}>
            确定要删除
            <strong style={{ color: 'var(--danger)' }}>
              「{models.find(m => m.id === deleteModelId)?.name || models.find(m => m.id === deleteModelId)?.model_name || `模型 #${deleteModelId}`}」
            </strong>
            吗？
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>删除后不可恢复，请谨慎操作</div>
        </div>
        <div className="modal-actions">
          <button className="btn btn-outline btn-sm" onClick={() => setDeleteModal(false)} disabled={deleting}>取消</button>
          <button className="btn btn-danger btn-sm" onClick={confirmDelete} disabled={deleting}><IconTrash /> {deleting ? '删除中...' : '确认删除'}</button>
        </div>
      </Modal>
    </div>
  )
}

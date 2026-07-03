import { useState, useEffect } from 'react'
import { apiGet, apiPost, apiDelete } from '../api'
import { IconBot, IconPlus, IconTrash, IconSave, IconSparkles, IconSettings, IconZap } from '../icons'
import Modal from '../components/Modal'

// SOUL: 性格特征标签 + 描述
const SOUL_TRAITS = [
  'friendly', 'professional', 'humorous', 'concise', 'detailed',
  'warm', 'creative', 'logical', 'patient', 'enthusiastic',
]
const SOUL_INFO = {
  friendly: { label: '友好', desc: '语气友善温和，让人感到亲切' },
  professional: { label: '专业', desc: '回答严谨准确，有技术深度' },
  humorous: { label: '幽默', desc: '轻松诙谐，适当加入俏皮话' },
  concise: { label: '简洁', desc: '回答直击要点，不啰嗦' },
  detailed: { label: '详细', desc: '展开说明，提供丰富细节' },
  warm: { label: '温暖', desc: '有温度，关心用户感受' },
  creative: { label: '创意', desc: '思维跳跃，提供新颖视角' },
  logical: { label: '理性', desc: '逻辑清晰，结构化分析' },
  patient: { label: '耐心', desc: '不厌其烦，循序渐进引导' },
  enthusiastic: { label: '热情', desc: '积极活跃，充满能量' },
}

// 角色定义：每个角色有独立的默认值，可被用户保存覆盖
const ROLES = [
  { key: 'companion', label: '贴心伙伴',
    soul: ['friendly', 'concise', 'warm'],
    identity: '我是你的贴心伙伴，一个友善热心的聊天助手。',
    userContext: '用户希望轻松愉快地聊天，不喜欢太正式或太冷淡的回复。',
    systemPrompt: '用温暖的语气回复，适当使用表情符号。如果用户情绪低落，主动安慰和鼓励。',
  },
  { key: 'expert', label: '技术专家',
    soul: ['professional', 'detailed', 'logical'],
    identity: '我是一个专业技术顾问，擅长深度分析和严谨解答。',
    userContext: '用户是技术人员，追求准确性和深度，反感敷衍的回答。',
    systemPrompt: '回答要有理有据，引用可靠来源。遇到不确定的信息要明确说明。使用结构化格式（如分点、表格）呈现复杂信息。',
  },
  { key: 'creative', label: '创意达人',
    soul: ['humorous', 'creative', 'enthusiastic'],
    identity: '我是一个创意达人，风趣幽默，充满奇思妙想。',
    userContext: '用户喜欢新颖有趣的内容，讨厌千篇一律的套话。',
    systemPrompt: '多用比喻、故事和生动的例子来表达观点。适当加入幽默和网络流行语。鼓励用户跳出常规思维。',
  },
  { key: 'mentor', label: '知识导师',
    soul: ['patient', 'detailed', 'warm'],
    identity: '我是你的知识导师，耐心细致，善于引导和讲解。',
    userContext: '用户是学习者，需要循序渐进地理解知识，不喜欢被直接给答案。',
    systemPrompt: '用苏格拉底式提问引导用户思考。把复杂概念拆解成简单的步骤。多用类比帮助理解。对用户的进步给予肯定和鼓励。',
  },
  { key: 'custom', label: '自定义',
    soul: [],
    identity: '',
    userContext: '',
    systemPrompt: '',
  },
]

/** 角色默认值速查表 */
const ROLE_DEFAULT = Object.fromEntries(ROLES.map(r => [r.key, { soul: [...r.soul], identity: r.identity, userContext: r.userContext, systemPrompt: r.systemPrompt }]))

export default function Bots() {
  const [bots, setBots] = useState([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)

  // Bot 新增/编辑弹窗
  const [botModal, setBotModal] = useState(false)
  const [editingBot, setEditingBot] = useState(null)
  const [botForm, setBotForm] = useState({ name: '', bot_token: '' })
  const [verifyStatus, setVerifyStatus] = useState('idle') // idle | loading | verified | error
  const [verifyInfo, setVerifyInfo] = useState(null)

  const [showToken, setShowToken] = useState(false)

  // Token 验证（防抖）
  const verifyToken = async (token) => {
    if (!token || token.length < 30) { setVerifyStatus('idle'); setVerifyInfo(null); return }
    setVerifyStatus('loading')
    try {
      const res = await apiPost('/bots/verify', { bot_token: token })
      setVerifyInfo(res)
      setVerifyStatus('verified')
      // 自动填入名称
      if (res.first_name) {
        setBotForm(f => ({ ...f, name: f.name || res.first_name + (res.username ? ` (@${res.username})` : '') }))
      }
    } catch (err) {
      setVerifyInfo({ error: err.message })
      setVerifyStatus('error')
    }
  }

  const handleTokenChange = (val) => {
    setBotForm(f => ({ ...f, bot_token: val }))
    setVerifyStatus('idle')
    setVerifyInfo(null)
    // 防抖 1 秒
    clearTimeout(window._tokenTimer)
    window._tokenTimer = setTimeout(() => verifyToken(val), 800)
  }

  // 性格弹窗 (SOUL + IDENTITY + USER + System Prompt)
  const [personaModal, setPersonaModal] = useState(false)
  const [personaBotId, setPersonaBotId] = useState(null)
  const [soul, setSoul] = useState([])
  const [identity, setIdentity] = useState('')
  const [userContext, setUserContext] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [savingPersona, setSavingPersona] = useState(false)

  // 设置弹窗
  const [settingsModal, setSettingsModal] = useState(false)
  const [settingsBotId, setSettingsBotId] = useState(null)
  const [settingsForm, setSettingsForm] = useState({ group_reply_mode: 'mentioned', max_history: '20', rate_limit: '10', reply_with_quote: '0', allowed_models: '[]' })
  const [modelsList, setModelsList] = useState([])
  const [savingSettings, setSavingSettings] = useState(false)

  // 删除确认弹窗
  const [deleteModal, setDeleteModal] = useState(false)
  const [deleteBotId, setDeleteBotId] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [tutorialModal, setTutorialModal] = useState(false)

  useEffect(() => { loadBots() }, [])

  const loadBots = () => {
    setLoading(true)
    apiGet('/bots').then(d => setBots(d.bots || [])).catch(console.error).finally(() => setLoading(false))
  }
  const showToast = (type, text) => { setToast({ type, text }); setTimeout(() => setToast(null), 3000) }

  // ===== Bot 增删改 =====
  const openAdd = () => { setEditingBot(null); setBotForm({ name: '', bot_token: '' }); setBotModal(true) }
  const openEdit = (b) => { setEditingBot(b.id); setBotForm({ name: b.name, bot_token: b.bot_token }); setBotModal(true) }
  const saveBot = async () => {
    try {
      if (editingBot) { await apiPost(`/bots/${editingBot}`, botForm); showToast('success', '已更新') }
      else { await apiPost('/bots', botForm); showToast('success', '已添加并上线') }
      setBotModal(false); loadBots()
    } catch (err) { showToast('error', err.message) }
  }
  const delBot = (id) => { setDeleteBotId(id); setDeleteModal(true) }
  const confirmDelete = async () => {
    setDeleting(true)
    try { await apiDelete(`/bots/${deleteBotId}`); setDeleteModal(false); showToast('success', '已删除'); loadBots() }
    catch (err) { showToast('error', err.message) }
    setDeleting(false)
  }
  const toggleBot = async (b) => { try { await apiPost(`/bots/${b.id}`, { is_active: !b.is_active }); setBots(prev => prev.map(x => x.id === b.id ? { ...x, is_active: !b.is_active } : x)) } catch (err) { showToast('error', err.message) } }

  // ===== 性格弹窗 =====
  // 每个角色独立存储：soul / identity / userContext / systemPrompt
  // 无默认值，首次进入为空表单
  const [activeRole, setActiveRole] = useState('')
  const [roleCache, setRoleCache] = useState({})  // { companion: {soul,identity,userContext,systemPrompt}, ... }

  const openPersona = async (b) => {
    setPersonaBotId(b.id)
    setActiveRole(''); setSoul([]); setIdentity(''); setUserContext(''); setSystemPrompt(''); setRoleCache({})
    const prefix = `${b.id}:`
    try {
      const data = await apiGet('/settings')
      // 读取角色数据（per-bot 优先，回退全局默认）
      const raw = data[`${prefix}persona_roles`] || data.persona_roles
      let saved = {}
      if (raw) {
        try { saved = JSON.parse(raw) } catch (e) {}
      }
      setRoleCache(saved)

      // 当前选中角色（per-bot → 全局 → 默认贴心伙伴）
      const role = data[`${prefix}personality_role`] || data.personality_role || 'companion'
      setActiveRole(role)
      // 前端默认值打底，全局/已保存数据覆盖
      const cur = { ...(ROLE_DEFAULT[role] || {}), ...(saved[role] || {}) }
      setSoul(cur.soul || [])
      setIdentity(cur.identity || '')
      setUserContext(cur.userContext || '')
      setSystemPrompt(cur.systemPrompt || '')
    } catch (e) {
      // 兜底：默认贴心伙伴
      const d = ROLE_DEFAULT.companion
      setActiveRole('companion'); setSoul(d.soul); setIdentity(d.identity); setUserContext(''); setSystemPrompt('')
    }
    setPersonaModal(true)
  }

  const handlePreset = (key) => {
    if (activeRole === key) return
    // 当前表单回写缓存
    setRoleCache(prev => ({
      ...prev,
      [activeRole]: { soul: [...soul], identity, userContext, systemPrompt },
    }))
    // 切换到目标角色（已保存优先，否则默认值）
    setActiveRole(key)
    const d = { ...(ROLE_DEFAULT[key] || {}), ...(roleCache[key] || {}) }
    setSoul(d.soul || [])
    setIdentity(d.identity || '')
    setUserContext(d.userContext || '')
    setSystemPrompt(d.systemPrompt || '')
  }

  const toggleSoul = (trait) => {
    setSoul(prev => prev.includes(trait) ? prev.filter(t => t !== trait) : [...prev, trait])
  }

  const resetToDefault = () => {
    const def = ROLE_DEFAULT[activeRole]
    if (!def) return
    setSoul([...def.soul])
    setIdentity(def.identity)
    setUserContext(def.userContext)
    setSystemPrompt(def.systemPrompt)
    setRoleCache(prev => { const next = { ...prev }; delete next[activeRole]; return next })
  }

  const savePersona = async () => {
    setSavingPersona(true)
    const prefix = `${personaBotId}:`
    const merged = { ...roleCache, [activeRole]: { soul: [...soul], identity, userContext, systemPrompt } }
    try {
      await apiPost('/settings/batch', {
        settings: {
          [`${prefix}persona_roles`]: JSON.stringify(merged),
          [`${prefix}personality_role`]: activeRole,
          [`${prefix}soul`]: JSON.stringify(soul),
          [`${prefix}identity`]: identity,
          [`${prefix}user_context`]: userContext,
          [`${prefix}bot_system_prompt`]: systemPrompt,
        }
      })
      showToast('success', '性格已保存')
      loadBots()
      setPersonaModal(false)
    } catch (err) { showToast('error', err.message) }
    setSavingPersona(false)
  }

  // ===== 设置弹窗 =====
  const openSettings = async (b) => {
    setSettingsBotId(b.id)
    setSettingsForm({ group_reply_mode: 'mentioned', max_history: '20', rate_limit: '10', reply_with_quote: '0', allowed_models: '[]' })
    setSettingsModal(true)
    const prefix = `${b.id}:`
    try {
      const data = await apiGet('/settings')
      setModelsList(data.model_configs || [])
      setSettingsForm({
        group_reply_mode: data[`${prefix}group_reply_mode`] || data.group_reply_mode || 'mentioned',
        max_history: data[`${prefix}max_history`] || data.max_history || '20',
        rate_limit: data[`${prefix}rate_limit`] || data.rate_limit || '10',
        reply_with_quote: data[`${prefix}reply_with_quote`] || data.reply_with_quote || '0',
        allowed_models: data[`${prefix}allowed_models`] || '[]',
      })
    } catch (e) { /* 默认值 */ }
  }
  const updateSetting = (k, v) => setSettingsForm(prev => ({ ...prev, [k]: v }))
  const toggleAllowedModel = (modelId) => {
    const current = JSON.parse(settingsForm.allowed_models || '[]')
    const updated = current.includes(modelId) ? current.filter(id => id !== modelId) : [...current, modelId]
    updateSetting('allowed_models', JSON.stringify(updated))
  }
  const saveSettings = async () => {
    setSavingSettings(true)
    const prefix = `${settingsBotId}:`
    try {
      await apiPost('/settings/batch', { settings: Object.fromEntries(Object.entries(settingsForm).map(([k, v]) => [`${prefix}${k}`, v])) })
      showToast('success', '设置已保存')
      setSettingsModal(false)
    } catch (err) { showToast('error', err.message) }
    setSavingSettings(false)
  }

  if (loading) return <div className="page-header"><h1>加载中...</h1></div>

  return (
    <div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.text}</div>}
      <button className="btn btn-primary" onClick={openAdd} style={{ marginBottom: 16, marginRight: 8 }}><IconPlus /> 添加 Bot</button>
      <button className="btn btn-outline" onClick={() => setTutorialModal(true)} style={{ marginBottom: 16 }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 4, verticalAlign: 'middle' }}>
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
        </svg>
        使用教程
      </button>

      {/* Bot 新增/编辑弹窗 */}
      <Modal open={botModal} onClose={() => setBotModal(false)} title={editingBot ? '编辑 Bot' : '添加 Bot'}>
        <div className="form-group">
          <label className="form-label">Bot Token</label>
          <div style={{ position: 'relative' }}>
            <input className="form-input" value={botForm.bot_token} type={showToken ? 'text' : 'password'}
              onChange={e => handleTokenChange(e.target.value)}
              placeholder="粘贴 @BotFather 获取的 Token（自动识别）"
              style={{ paddingRight: 40 }} />
            <button type="button" onClick={() => setShowToken(s => !s)}
              style={{
                position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)',
                background: 'none', border: 'none', cursor: 'pointer', padding: 4, lineHeight: 1,
                color: 'var(--text-muted)', display: 'flex', alignItems: 'center',
              }}
              title={showToken ? '隐藏 Token' : '显示 Token'}>
              {showToken ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                  <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                  <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/>
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              )}
            </button>
          </div>
          <div className="form-hint">
            {verifyStatus === 'loading' && <span style={{ color: 'var(--primary)' }}>正在验证...</span>}
            {verifyStatus === 'verified' && verifyInfo && <span style={{ color: 'var(--success)' }}>@{verifyInfo.username} 验证通过</span>}
            {verifyStatus === 'error' && verifyInfo && <span style={{ color: 'var(--danger)' }}>{verifyInfo.error}</span>}
            {verifyStatus === 'idle' && '输入后自动验证'}
          </div>
        </div>
        <div className="form-group"><label className="form-label">名称</label><input className="form-input" value={botForm.name} onChange={e => setBotForm({ ...botForm, name: e.target.value })} placeholder="Bot 显示名称（自动填入）" /></div>
        <div className="modal-actions"><button className="btn btn-outline btn-sm" onClick={() => setBotModal(false)}>取消</button><button className="btn btn-primary btn-sm" onClick={saveBot}><IconSave /> 保存</button></div>
      </Modal>

      {/* 性格弹窗: SOUL + IDENTITY + System Prompt */}
      <Modal open={personaModal} onClose={() => setPersonaModal(false)}
        title={`${bots.find(b => b.id === personaBotId)?.name || `Bot #${personaBotId}`} 性格设置`} width="750px">
        {/* 角色选择 */}
        <div className="role-tabs" style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          {ROLES.map(r => (
            <button key={r.key}
              onClick={() => handlePreset(r.key)}
              style={{
                padding: '5px 12px', fontSize: 13, borderRadius: 8, cursor: 'pointer',
                border: `1.5px solid ${activeRole === r.key ? 'var(--primary)' : 'var(--border)'}`,
                background: activeRole === r.key ? 'var(--primary-light)' : 'transparent',
                color: activeRole === r.key ? 'var(--primary)' : 'var(--text-secondary)',
                fontWeight: activeRole === r.key ? 600 : 400,
                transition: 'all .15s',
              }}
            >
              {r.label}
            </button>
          ))}
        </div>

        {/* SOUL: 性格标签 */}
        <div className="form-group">
          <label className="form-label">性格特征 (SOUL)</label>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {SOUL_TRAITS.map(trait => (
              <span key={trait} title={SOUL_INFO[trait].desc}
                onClick={() => toggleSoul(trait)}
                className={`badge ${soul.includes(trait) ? 'badge-success' : 'badge-default'}`}
                style={{ cursor: 'pointer', fontSize: 12, padding: '4px 10px' }}>
                {SOUL_INFO[trait].label}
              </span>
            ))}
          </div>
          <div className="form-hint">鼠标悬停查看含义，点击选中</div>
          {soul.length > 0 && (
            <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
              已选: {soul.map(t => `${SOUL_INFO[t].label}(=${SOUL_INFO[t].desc})`).join('，')}
            </div>
          )}
        </div>

        {/* IDENTITY: 身份描述 */}
        <div className="form-group">
          <label className="form-label">身份描述 (IDENTITY)</label>
          <input className="form-input" value={identity} onChange={e => setIdentity(e.target.value)}
            placeholder="如: 我是一个友好的 Telegram 聊天机器人" />
          <div className="form-hint">告诉我「我是谁」，一句简短的身份声明</div>
        </div>

        {/* USER: 用户描述 */}
        <div className="form-group">
          <label className="form-label">用户描述 (USER)</label>
          <input className="form-input" value={userContext} onChange={e => setUserContext(e.target.value)}
            placeholder="如: 用户是开发者，喜欢简洁回复，经常聊技术话题" />
          <div className="form-hint">告诉我「用户是谁」，让 AI 更有针对性地回复</div>
        </div>

        {/* System Prompt 补充 */}
        <div className="form-group">
          <label className="form-label">System Prompt（可选补充）</label>
          <textarea className="form-textarea" rows={4} value={systemPrompt}
            onChange={e => setSystemPrompt(e.target.value)}
            placeholder="额外的行为指令，留空则只用上面结构化字段" />
        </div>

        <div className="modal-actions">
          <button className="btn btn-outline btn-sm" onClick={resetToDefault} style={{ color: 'var(--danger)' }}>恢复默认</button>
          <div style={{ flex: 1 }} />
          <button className="btn btn-outline btn-sm" onClick={() => setPersonaModal(false)}>取消</button>
          <button className="btn btn-primary btn-sm" onClick={savePersona} disabled={savingPersona}><IconSave /> 保存</button>
        </div>
      </Modal>

      {/* 聊天设置弹窗 */}
      <Modal open={settingsModal} onClose={() => setSettingsModal(false)}
        title={`${bots.find(b => b.id === settingsBotId)?.name || `Bot #${settingsBotId}`} 聊天设置`} width="500px">

        <div className="form-group">
          <label className="form-label">群聊回复模式</label>
          <select className="form-select" value={settingsForm.group_reply_mode} onChange={e => updateSetting('group_reply_mode', e.target.value)}>
            <option value="off">关闭（不回复群聊）</option>
            <option value="mentioned">仅 @提及 时回复</option>
            <option value="all">回复所有消息</option>
          </select>
          <div className="form-hint">私聊始终自动回复，不受此设置影响</div>
        </div>

        <div className="form-group">
          <label className="form-label">上下文记忆轮数</label>
          <input className="form-input" type="number" min={1} max={100} value={settingsForm.max_history} onChange={e => updateSetting('max_history', e.target.value)} />
          <div className="form-hint">保留最近 N 轮对话，越多越费 Token</div>
        </div>

        <div className="form-group">
          <label className="form-label">频率限制（次/分钟，0=不限制）</label>
          <input className="form-input" type="number" min={0} max={60} value={settingsForm.rate_limit} onChange={e => updateSetting('rate_limit', e.target.value)} />
          <div className="form-hint">同一用户每分钟最多 N 条消息，超出忽略</div>
        </div>

        <div className="form-group">
          <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <label className="toggle"><input type="checkbox" checked={settingsForm.reply_with_quote === '1'} onChange={e => updateSetting('reply_with_quote', e.target.checked ? '1' : '0')} /><span className="toggle-slider"></span></label>
            回复时引用原消息
          </label>
          <div className="form-hint">关闭后直接发送，不显示引用框</div>
        </div>

        <div className="form-group">
          <label className="form-label">指定模型（留空=使用全局默认）</label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {modelsList.length === 0 && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>暂无可用模型，请先在模型管理页面配置</span>}
            {modelsList.map(m => {
              const selectedIds = JSON.parse(settingsForm.allowed_models || '[]')
              const idx = selectedIds.indexOf(m.id)
              const checked = idx !== -1
              return (
                <label key={m.id} style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px',
                  borderRadius: 6, cursor: 'pointer', fontSize: 13,
                  background: checked ? 'var(--primary-light)' : 'transparent',
                  border: `1px solid ${checked ? 'var(--primary)' : 'var(--border)'}`,
                }}>
                  <input type="checkbox" checked={checked} onChange={() => toggleAllowedModel(m.id)}
                    style={{ accentColor: 'var(--primary)' }} />
                  <span>{m.name}</span>
                  <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 4 }}>{m.provider} · {m.model}</span>
                  <div style={{ flex: 1 }} />
                  <span className={`badge ${checked ? (idx === 0 ? 'badge-success' : 'badge-default') : ''}`}
                    style={{
                      visibility: checked ? 'visible' : 'hidden',
                    }}>{idx === 0 ? '主' : '备用'}</span>
                </label>
              )
            })}
          </div>
          <div className="form-hint">按点击顺序排序，首次点击主模型，其次为备用。不选则使用全部可用模型</div>
        </div>

        <div className="modal-actions">
          <button className="btn btn-outline btn-sm" onClick={() => setSettingsModal(false)}>取消</button>
          <button className="btn btn-primary btn-sm" onClick={saveSettings} disabled={savingSettings}><IconSave /> 保存</button>
        </div>
      </Modal>

      {/* 删除确认弹窗 */}
      <Modal open={deleteModal} onClose={() => !deleting && setDeleteModal(false)}
        title={`删除 Bot`} width="400px">
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <div style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.8, marginBottom: 8 }}>
            确定要删除
            <strong style={{ color: 'var(--danger)' }}>
              「{bots.find(b => b.id === deleteBotId)?.name || `Bot #${deleteBotId}`}」
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

      {/* Bot 列表 */}
      <div className="card">
        <div className="card-header"><IconBot /> Bot 列表 ({bots.length})</div>
        {bots.length === 0 ? (
          <div className="empty-state"><IconBot /><p>暂无 Bot，请添加</p></div>
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead><tr><th>ID</th><th>名称</th><th>Token</th><th>状态</th><th>操作</th></tr></thead>
              <tbody>
                {bots.map(b => (
                  <tr key={b.id}>
                    <td>{b.id}</td>
                    <td>{b.name || '-'}</td>
                    <td><code>{b.bot_token ? b.bot_token.slice(0, 16) + '...' : '-'}</code></td>
                    <td>
                      <label className="toggle toggle-sm" style={{ verticalAlign: 'middle' }}>
                        <input type="checkbox" checked={!!b.is_active} onChange={() => toggleBot(b)} />
                        <span className="toggle-slider"></span>
                      </label>
                      <span style={{ marginLeft: 6, fontSize: 12, color: b.is_active ? 'var(--success)' : 'var(--text-muted)' }}>{b.is_active ? '启用' : '禁用'}</span>
                    </td>
                    <td>
                      <div className="action-btns" style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        <button className="btn btn-outline btn-sm" onClick={() => openPersona(b)}><IconSparkles /> 性格</button>
                        <button className="btn btn-outline btn-sm" onClick={() => openSettings(b)}><IconSettings /> 设置</button>
                        <button className="btn btn-outline btn-sm" onClick={() => openEdit(b)}><IconSave /> 编辑</button>
                        <button className="btn btn-outline btn-sm" onClick={() => delBot(b.id)}><IconTrash /> 删除</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Bot 创建教程弹窗 */}
      <Modal open={tutorialModal} onClose={() => setTutorialModal(false)}
        title="Bot 创建教程" width="650px">
        <div style={{ fontSize: 13, lineHeight: 2, color: 'var(--text-secondary)' }}>
          <div style={{ marginBottom: 16 }}>
            <strong style={{ fontSize: 14, color: 'var(--text)' }}>第一步：向 @BotFather 创建 Bot</strong>
            <div style={{ paddingLeft: 16, marginTop: 4 }}>
              1. 在 Telegram 中搜索并打开 <strong>@BotFather</strong><br />
              2. 发送 <code style={{ background: 'var(--bg)', padding: '1px 6px', borderRadius: 4 }}>/newbot</code> 开始创建<br />
              3. 按提示输入 Bot 名称（如"我的助手"）和用户名（如 my_assistant_bot）<br />
              4. 创建成功后 @BotFather 会返回一个 Token，类似：<br />
              <code style={{ background: 'var(--bg)', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>
                123456789:ABCdefGHIjklMNOpqrsTUVwxyz
              </code>
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <strong style={{ fontSize: 14, color: 'var(--text)' }}>第二步：在此面板添加 Bot</strong>
            <div style={{ paddingLeft: 16, marginTop: 4 }}>
              1. 点击页面顶部的 <strong>「添加 Bot」</strong> 按钮<br />
              2. 粘贴上一步获取的 Token，系统会自动验证 Bot 信息<br />
              3. 输入 Bot 显示名称（自动填入 @BotFather 返回的用户名）<br />
              4. 点击「保存」完成添加
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <strong style={{ fontSize: 14, color: 'var(--text)' }}>第三步：配置 Bot（可选）</strong>
            <div style={{ paddingLeft: 16, marginTop: 4 }}>
              <strong><span style={{ display: 'inline-flex', width: 16, height: 16, verticalAlign: 'middle' }}><IconSparkles /></span> 性格设置：</strong>选择预设或自定义 Bot 的性格特征、身份描述和回复风格<br />
              <strong><span style={{ display: 'inline-flex', width: 16, height: 16, verticalAlign: 'middle' }}><IconSettings /></span> 聊天设置：</strong>
              <div style={{ paddingLeft: 12 }}>
                · 群聊回复模式：关闭 / 仅@提及回复 / 回复所有消息<br />
                · 上下文记忆轮数：保留最近 N 轮对话（建议 10~20）<br />
                · 频率限制：每用户每分钟最多消息数<br />
                · 指定模型：选择 Bot 使用的 AI 模型（留空使用全局默认）
              </div>
            </div>
          </div>

          <div>
            <strong style={{ fontSize: 14, color: 'var(--text)' }}>第四步：启用并测试</strong>
            <div style={{ paddingLeft: 16, marginTop: 4 }}>
              1. 在 Bot 列表中点击 <strong>开关</strong> 启用 Bot<br />
              2. 在 Telegram 中找到你的 Bot，发送消息测试<br />
              3. 如果是群聊，需要将 Bot 拉入群并设置回复模式为「仅 @提及」或「所有消息」
            </div>
          </div>

          <div style={{ marginTop: 16, padding: '10px 14px', background: 'var(--primary-light)', borderRadius: 8, fontSize: 12, color: 'var(--primary)' }}>
            <span style={{ display: 'inline-flex', width: 14, height: 14, verticalAlign: 'middle' }}><IconZap /></span> 提示：Token 是 Bot 的钥匙，请勿泄露。如果 Token 泄露，可在 @BotFather 中使用 <code style={{ background: 'var(--bg)', padding: '1px 6px', borderRadius: 4 }}>/revoke</code> 废弃旧 Token。
          </div>
        </div>
      </Modal>
    </div>
  )
}

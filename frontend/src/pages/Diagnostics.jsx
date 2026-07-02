import { useState, useEffect } from 'react'
import { apiGet } from '../api'
import { IconActivity, IconBot } from '../icons'

export default function Diagnostics() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiGet('/diagnostics').then(setData).catch(console.error).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="page-header"><h1>加载中...</h1></div>

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label"><IconBot /> Bot 总数</div>
          <div className="stat-value">{data?.total_bots || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label" style={{ color: 'var(--success)' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14"><polyline points="20 6 9 17 4 12"/></svg> 活跃
          </div>
          <div className="stat-value">{data?.active_bots || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label"><IconActivity /> 运行中</div>
          <div className="stat-value">{data?.running_instances || 0}</div>
        </div>
      </div>

      {(data?.bots || []).map(b => (
        <div key={b.id} className="card" style={{ marginBottom: 12 }}>
          <div className="card-header">
            <IconBot /> Bot #{b.id}: {b.name || '未命名'}
            <span className={`badge ${b.is_running ? 'badge-success' : b.is_active ? 'badge-warning' : 'badge-default'}`} style={{ marginLeft: 8 }}>
              {b.is_running ? '运行中' : b.is_active ? '异常' : '已禁用'}
            </span>
          </div>
          <table className="table">
            <thead><tr><th>检测项</th><th>状态</th><th>说明</th></tr></thead>
            <tbody>
              {(b.checks || []).map((c, i) => (
                <tr key={i}>
                  <td>{c.item}</td>
                  <td>
                    {c.ok === true
                      ? <span style={{ color: 'var(--success)' }}>
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14" style={{verticalAlign:'middle',marginRight:4}}><polyline points="20 6 9 17 4 12"/></svg> 正常
                        </span>
                      : c.ok === false
                      ? <span style={{ color: 'var(--danger)' }}>
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14" style={{verticalAlign:'middle',marginRight:4}}><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg> 异常
                        </span>
                      : <span style={{ color: 'var(--text-muted)' }}>--</span>}
                  </td>
                  <td style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{c.msg}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      <div className="card">
        <div className="card-header"><IconActivity /> 常见问题排查</div>
        <table className="table">
          <thead><tr><th>问题</th><th>原因</th><th>解决方法</th></tr></thead>
          <tbody>
            <tr><td>群聊不回复</td><td>隐私模式未关闭</td><td>@BotFather → Bot Settings → Group Privacy → Turn off</td></tr>
            <tr><td>获取不到群人数</td><td>Bot 不是管理员</td><td>将 Bot 设为群管理员</td></tr>
            <tr><td>Conflict 错误</td><td>多个实例在轮询</td><td>docker compose restart dev</td></tr>
            <tr><td>模型不可用</td><td>API Key 未配置</td><td>模型配置页填写 Key</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { apiGet } from '../api'
import { IconActivity, IconZap, IconUsers, IconMessage } from '../icons'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiGet('/dashboard').then(setData).catch(console.error).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="page-header"><h1>加载中...</h1></div>

  const s = data?.stats_7d || {}
  const models = data?.models || []
  const plugins = data?.plugins || []

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label"><IconMessage /> 消息数 (7天)</div>
          <div className="stat-value">{s.total_messages || 0}</div>
          <div className="stat-sub">30天: {data?.stats_30d?.total_messages || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label"><IconZap /> Token 消耗 (7天)</div>
          <div className="stat-value">{(s.total_tokens || 0).toLocaleString()}</div>
          <div className="stat-sub">30天: {(data?.stats_30d?.total_tokens || 0).toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label"><IconUsers /> 活跃用户</div>
          <div className="stat-value">{s.unique_users || 0}</div>
          <div className="stat-sub">会话数: {data?.total_sessions || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label"><IconActivity /> 模型后端</div>
          <div className="stat-value">{data?.available_backends?.length || 0}</div>
          <div className="stat-sub">{data?.available_backends?.join(', ') || '无'}</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><IconZap /> 模型概览</div>
          {models.length === 0 ? <div className="empty-state">暂无配置</div> : (
            <table className="table">
              <thead><tr><th>供应商</th><th>模型</th><th>状态</th></tr></thead>
              <tbody>
                {models.map((m, i) => (
                  <tr key={i}>
                    <td><span className="badge badge-default">{m.provider}</span></td>
                    <td>{m.model_name || '-'}</td>
                    <td><span className={`badge ${m.is_enabled ? 'badge-success' : 'badge-default'}`}>
                      {m.is_enabled ? '启用' : '未启用'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div className="card">
          <div className="card-header"><IconActivity /> 按模型统计 (7天)</div>
          {(!s.by_model || s.by_model.length === 0) ? <div className="empty-state">暂无数据</div> : (
            <table className="table">
              <thead><tr><th>模型</th><th>调用次数</th><th>Token</th></tr></thead>
              <tbody>
                {s.by_model.map((m, i) => (
                  <tr key={i}><td>{m.model || '?'}</td><td>{m.count}</td><td>{m.tokens.toLocaleString()}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header"><IconZap /> 连接器状态 ({plugins.filter(p => p.enabled).length}/{plugins.length})</div>
        {plugins.map(p => (
          <div key={p.name} className="plugin-row">
            <div className="plugin-info"><h4>{p.name}</h4></div>
            <span className={`badge ${p.enabled ? 'badge-success' : 'badge-default'}`}>
              {p.enabled ? '开启' : '关闭'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

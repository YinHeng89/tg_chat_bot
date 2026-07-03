const apiBase = '/api'

async function request(path, options = {}) {
  const token = localStorage.getItem('admin_token') || ''
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...options.headers,
  }

  const res = await fetch(`${apiBase}${path}`, {
    ...options,
    headers,
  })

  if (res.status === 401) {
    localStorage.removeItem('admin_token')
    window.location.reload()
    throw new Error('认证已过期')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '请求失败' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }

  return res.json()
}

export function apiGet(path) {
  return request(path)
}

export function apiPost(path, data) {
  return request(path, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function apiDelete(path) {
  return request(path, { method: 'DELETE' })
}

export async function login(password) {
  const res = await fetch(`${apiBase}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '登录失败' }))
    throw new Error(err.detail || '登录失败')
  }
  return res.json()
}

export async function checkSetup() {
  const res = await fetch(`${apiBase}/auth/status`)
  return res.json()
}

export async function setupPassword(password) {
  const res = await fetch(`${apiBase}/auth/setup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '设置失败' }))
    throw new Error(err.detail || '设置失败')
  }
  return res.json()
}

export async function resetPassword(recoveryCode, newPassword) {
  const res = await fetch(`${apiBase}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recovery_code: recoveryCode, new_password: newPassword }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '重置失败' }))
    throw new Error(err.detail || '重置失败')
  }
  return res.json()
}

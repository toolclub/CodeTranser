import axios, { AxiosError, type AxiosInstance, type AxiosResponse } from 'axios'

import router from '@/router'
import type { ApiResponse } from '@/types'

const http: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30_000,
})

// 请求拦截:dev 模式注入 base64(sub+roles) bearer(对齐后端 sso_adapter 的 dev. 前缀旁路)
http.interceptors.request.use((cfg) => {
  if (import.meta.env.DEV) {
    const claims = {
      sub: 'u_dev',
      preferred_username: 'dev',
      name: 'Dev',
      email: 'dev@local',
      roles: ['admin'],
    }
    const b64 = btoa(unescape(encodeURIComponent(JSON.stringify(claims)))).replace(/=+$/, '')
    cfg.headers = cfg.headers ?? {}
    ;(cfg.headers as Record<string, string>)['Authorization'] = `Bearer dev.${b64}`
  }
  return cfg
})

// 响应拦截:401/403 跳 /no-permission
http.interceptors.response.use(
  (r) => r,
  (err: AxiosError<ApiResponse>) => {
    const status = err.response?.status
    if (status === 401 || status === 403) router.push('/no-permission').catch(() => {})
    return Promise.reject(err)
  },
)

/** 把 ApiResponse<T> 解包成 T;失败 throw 带 error_code 的 Error */
export async function unwrap<T>(p: Promise<AxiosResponse<ApiResponse<T>>>): Promise<T> {
  try {
    const r = await p
    const body = r.data
    if (body.code !== 0 && body.code !== undefined) {
      throw Object.assign(new Error(body.message || 'api error'), {
        code: body.error_code,
        data: body.data,
      })
    }
    return (body.data ?? (null as unknown)) as T
  } catch (e) {
    if (axios.isAxiosError(e) && e.response?.data) {
      const body = e.response.data as ApiResponse
      throw Object.assign(new Error(body.message || 'api error'), {
        code: body.error_code,
        data: body.data,
      })
    }
    throw e
  }
}

export default http

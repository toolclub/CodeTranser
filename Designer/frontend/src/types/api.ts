// 后端 ApiResponse
export interface ApiResponse<T = unknown> {
  code: number
  message?: string
  error_code?: string
  data: T | null
  trace_id?: string | null
}

export interface ApiError {
  code: number
  error_code: string
  message: string
  data: unknown
  trace_id: string | null
}

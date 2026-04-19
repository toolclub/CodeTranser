import http, { unwrap } from './client'

export interface Review {
  id: string
  run_id: string
  reviewer_id: number
  verdict: 'approved' | 'rejected' | 'needs_revision' | null
  summary: string
  finished_at: string | null
  created_at: string
}

export interface ReviewComment {
  id: string
  review_id: string
  author_id: number
  target_type: string
  target_ref: string
  body: string
  resolved: boolean
  created_at: string
}

export const reviewsApi = {
  get: (id: string) => unwrap<Review>(http.get(`/reviews/${id}`)),
  listComments: (id: string) =>
    unwrap<ReviewComment[]>(http.get(`/reviews/${id}/comments`)),
  postComment: (
    id: string,
    body: { target_type: string; target_ref: string; body: string },
  ) => unwrap<{ ok: boolean }>(http.post(`/reviews/${id}/comments`, body)),
  setVerdict: (
    id: string,
    body: { verdict: 'approved' | 'rejected' | 'needs_revision'; summary?: string },
  ) => unwrap<{ ok: boolean }>(http.post(`/reviews/${id}/verdict`, body)),
}

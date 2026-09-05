import type { QueryPlan, ResultEnvelope } from './types'

export interface PlannerResponse {
  plan: QueryPlan | null
  planner: 'azure' | 'explicit'
  warnings: string[]
}

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function interpretQuestion(question: string, signal?: AbortSignal): Promise<PlannerResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
  const response = await fetch(`${baseUrl}/v1/query/plan`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ question }),
    signal,
  })
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const detail = typeof body === 'object' && body && 'detail' in body ? String(body.detail) : response.statusText
    throw new ApiError(response.status, detail)
  }
  return response.json() as Promise<PlannerResponse>
}

export async function exportEvidence(result: ResultEnvelope): Promise<Blob> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
  const response = await fetch(`${baseUrl}/v1/export`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ envelope: result, rows: result.data, generated_at: new Date().toISOString() }) })
  if (!response.ok) throw new ApiError(response.status, response.statusText)
  return response.blob()
}

export async function executeQuery(plan: QueryPlan, signal?: AbortSignal): Promise<ResultEnvelope> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
  const response = await fetch(`${baseUrl}/v1/query/execute`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(plan),
    signal,
  })
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const detail = typeof body === 'object' && body && 'detail' in body ? String(body.detail) : response.statusText
    throw new ApiError(response.status, detail)
  }
  return response.json() as Promise<ResultEnvelope>
}
